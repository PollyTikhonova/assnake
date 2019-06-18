import yaml
import os
import glob
import pandas as pd
import loaders as loaders

class SampleSet:
    """
    Class that agglomerates samles and provides convinience functions for different tasks.
    """
    dir_of_this_file = os.path.dirname(os.path.abspath(__file__))

    # prefix, df, preproc, fs_name
    samples_pd = pd.DataFrame(columns=['df', 'fs_name', 'preproc', 'preprocs', 'reads', 'sample'])
    reads_info = pd.DataFrame()
    wc_config = {}
    config = {}

    wc_config_loc = os.path.join(dir_of_this_file, '../wc_config.yaml')
    with open(wc_config_loc, 'r') as stream:
        try:
            wc_config = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    config_loc = os.path.join(dir_of_this_file, '../config.yml')
    with open(config_loc, 'r') as stream:
        try:
            config = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

        
    def add_samples(self, prefix, df, preproc, samples = [], do_not_add = [], pattern = ''):
        samples = []
        fs_names = [f.split('/')[-1] for f in glob.glob(self.wc_config['sample_dir_wc'].format(prefix=prefix, df=df, preproc=preproc, sample = '*'))]

        if pattern != '':
            fs_names = [f.split('/')[-1] for f in 
            glob.glob(self.wc_config['sample_dir_wc'].format(prefix=prefix, df=df, preproc=preproc, sample = pattern))]

        if len(samples) > 0:
            for s in samples:
                if s in fs_names:
                    samples.append(loaders.load_sample(prefix, df, preproc, s))
        else:
            for fs_name in fs_names:
                if not (fs_name in do_not_add):
                    sample = loaders.load_sample(prefix, df, preproc, fs_name)
                    sample.update({'prefix': prefix})
                    samples.append(sample)     

        samples_pd = pd.DataFrame(samples)
        samples_pd.index = samples_pd['fs_name'] + ':' + samples_pd['preproc']

        self.samples_pd = pd.concat([self.samples_pd, samples_pd])
        self.reads_info = pd.DataFrame(self.samples_pd['reads'])

    def prepare_fastqc_list_multiqc(self, strand, set_name):
        fastqc_list = []

        for s in self.samples_pd.to_dict(orient='records'):
            fastqc_list.append(self.wc_config['fastqc_data_wc'].format(**s, strand=strand))

        dfs = list(set(self.samples_pd['df']))
        
        if len(dfs) == 1:
            prefix = list(set(self.samples_pd['prefix']))[0]
            sample_list = self.wc_config['multiqc_fatqc_wc'].format(
                df = dfs[0], 
                prefix = prefix, 
                strand = strand,
                sample_set=set_name)
            print(sample_list)
            
            multiqc_dir = os.path.dirname(sample_list)
            if not os.path.isdir(multiqc_dir):
                os.makedirs(multiqc_dir)
            with open(sample_list, 'x') as file:
                file.writelines('\n'.join(fastqc_list)) 

        return fastqc_list

    def prepare_dada2_sample_list(self, set_name):
        dada2_set_dir = os.path.join(self.config['dada2_dir'], set_name)

        dada2_dicts = []
        for s in self.samples_pd.to_dict(orient='records'):
            dada2_dicts.append(dict(mg_sample=s['fs_name'],
            R1 = self.wc_config['fastq_gz_file_wc'].format(prefix=s['prefix'], df=s['df'], preproc=s['preproc'], sample = s['fs_name'], strand = 'R1'), 
            R2 = self.wc_config['fastq_gz_file_wc'].format(prefix=s['prefix'], df=s['df'], preproc=s['preproc'], sample = s['fs_name'], strand = 'R2'),
            merged = self.wc_config['dada2_merged_wc'].format(prefix=s['prefix'], df=s['df'], preproc=s['preproc'], sample = s['fs_name'], sample_set = set_name)))
        if not os.path.exists(dada2_set_dir):
            os.mkdir(dada2_set_dir)

        dada2_df = pd.DataFrame(dada2_dicts)
        dada2_df.to_csv(os.path.join(dada2_set_dir, 'samples.tsv'), sep='\t', index=False)

    def prepare_assembly_set(self, assembler, params, set_name):
        # prepare dataframe
        samples = self.samples_pd[['df', 'fs_name', 'preproc']]
        samples = samples.rename({'fs_name': 'sample'}, axis=1)

        # Here we select df and prefix where the list will be saved. What to do if thre is more than 1 df i the list?
        dfs = list(set(self.samples_pd['df']))
        prefix = list(set(self.samples_pd['prefix']))[0]

        sample_table_loc = self.wc_config['assembly_table_wc'].format(
                df = dfs[0], 
                prefix = prefix, 
                assembler = assembler,
                params = params,
                sample_set=set_name)

        sample_table_dir = os.path.dirname(sample_table_loc)
        if not os.path.isdir(sample_table_dir):
            os.makedirs(sample_table_dir)
        samples.to_csv(sample_table_loc, sep='\t', index=False)

        # for s in self.samples:
        #     fastqc_list.append(self.wc_config['fastqc_data_wc'].format(**s, strand=strand))

        # 
        
        # if len(dfs) == 1:
        #     prefix = list(set(self.samples_df['prefix']))[0]
        #     sample_list = self.wc_config['multiqc_fatqc_wc'].format(
        #         df = dfs[0], 
        #         prefix = prefix, 
        #         strand = strand,
        #         sample_set=set_name)
        #     print(sample_list)
            
        #     multiqc_dir = os.path.dirname(sample_list)
        #     if not os.path.isdir(multiqc_dir):
        #         os.makedirs(multiqc_dir)
        #     with open(sample_list, 'x') as file:
        #         file.writelines('\n'.join(fastqc_list)) 


    def __str__(self):
        print('Number of samples: ', len(self.samples_pd))

    def __repr__(self):
        return 'Number of samples: ' +  str(len(self.samples_pd))

    