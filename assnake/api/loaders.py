import os
import glob

import pandas as pd
import numpy as np
# import assnake.api.bb_stats
# import sample_set
import yaml

import assnake.utils

def load_count(fs_prefix, df, preproc, sample, report_bps=False, verbose=False, count_wc=''):
    """
    Loads information about read and bp count in paired-end sample.
    """
    strands = ['R1', 'R2']
    count_loc1 = count_wc.format(fs_prefix=fs_prefix, df=df, preproc=preproc, sample=sample, strand=strands[0])
    count_loc2 = count_wc.format(fs_prefix=fs_prefix, df=df, preproc=preproc, sample=sample, strand=strands[1])
    
    count_dict = {'reads': -1}

    try:
        with open(count_loc1, 'r') as f:
            line = f.readline().rstrip()
            count_dict['reads'] += int(line.split(' ')[0]) + 1
            if report_bps:
                count_dict.update({'bps':int(line.split(' ')[1])})
        with open(count_loc2, 'r') as f:
            line = f.readline().rstrip()
            count_dict['reads'] += int(line.split(' ')[0])
            if report_bps:
                count_dict['bps'] += int(line.split(' ')[1])
    except:
        if verbose: 
            print('error loading counts: ', sample)
        if report_bps:
            count_dict.update({'bps': -1})
        return count_dict
    
    return count_dict
        

def load_dfs_from_db(db_loc):
    """
    Returns dict of dictionaries with info about datasets from fs database. Key - df name
    Mandatory fields: df, prefix
    """
    dfs = {}
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    config = assnake.utils.load_config_file()
    df_info_locs = glob.glob(config['assnake_db']+'/datasets/*/df_info.yaml')
    
    for df_info in df_info_locs:
        with open(df_info, 'r') as stream:
            try:
                info = yaml.load(stream, Loader=yaml.FullLoader)
                if 'df' in info:
                    dfs.update({info['df']: info})
            except yaml.YAMLError as exc:
                print(exc)
    return dfs

def load_df_from_db(df_name, db_loc='', include_preprocs = False):
    """
    Returns one dictionary with df info
    """
    config = assnake.utils.load_config_file()

    df_info_loc = config['assnake_db']+'/datasets/{df}/df_info.yaml'.format(df = df_name)
    df_info = {}
    with open(df_info_loc, 'r') as stream:
        try:
            info = yaml.load(stream, Loader=yaml.FullLoader)
            if 'df' in info:
                df_info =  info
        except yaml.YAMLError as exc:
            print(exc)

    reads_dir = os.path.join(df_info['fs_prefix'], df_info['df'], 'reads/*')
    preprocs = [p.split('/')[-1] for p in glob.glob(reads_dir)]
    preprocessing = {}
    if include_preprocs:
        for p in preprocs:
            samples = assnake.core.sample_set.SampleSet(df_info['fs_prefix'], df_info['df'], p)
            samples = samples.samples_pd[['fs_name', 'reads']].to_dict(orient='records')
            preprocessing.update({p:samples})
    df_info.update({"preprocs": preprocessing})
    return df_info

def load_sample(fs_prefix, df, preproc, sample,
                report_bps=False, report_size=False, verbose=False,
                sample_dir_wc = '', fastq_gz_file_wc = '', count_wc=''):
    '''
    Loads all necessary info about given sample from file system.
    '''
    # Init start values
    sample_dict = {}
    strands = ['R1', 'R2']
    
    final_preproc = ''
    size = 0
    containers = []
    preprocs = []


    # Now select what preprocessing we want to use
    if preproc == 'longest':
        preprocs = [p.split('/')[-2] for p in 
                    glob.glob(fastq_gz_file_wc.format(fs_prefix=fs_prefix, df=df, preproc='*', sample=sample, strand='R1'))]
    else:
        preprocs = [p.split('/')[-2] for p in 
                    glob.glob(fastq_gz_file_wc.format(fs_prefix=fs_prefix, df=df, preproc=preproc, sample=sample, strand='R1'))]
    for p in preprocs:
        r1 = fastq_gz_file_wc.format(fs_prefix=fs_prefix, df=df, preproc=p, sample=sample, strand=strands[0])
        r2 = fastq_gz_file_wc.format(fs_prefix=fs_prefix, df=df, preproc=p, sample=sample, strand=strands[1])

        if os.path.isfile(r1) and os.path.isfile(r2):
            containers.append(p)
            if len(p) > len(final_preproc):
                final_preproc = p
                if report_size:
                    size = os.path.getsize(r1) + os.path.getsize(r2)
                    sample_dict.update({'size': bytes2human(size, symbols='iec'), 'bytes': size})
    return {'df':df, 
            'fs_name':sample, 
            'sample':sample,  
            'preproc':final_preproc, 
            'fs_prefix': fs_prefix,
            #'preprocs':containers, 
            **load_count(fs_prefix, df, final_preproc, sample, verbose, count_wc=count_wc)}


fields = ['sample', 'sequencing_run']


def update_fs_samples_csv(dataset):
    '''
    Scans dataset folder and updates fs_samples.tsv if necessary
    
    :param dataset: Name of the dataset
    :return: Returns sample dict in loc
    
    '''
    fs_samples_tsv_loc = '{config}/datasets/{df}/fs_samples.tsv'.format(config=utils.load_config_file()['assnake_db'], df=dataset)
    df = Dataset(dataset)
    fs_samples_pd = pd.concat(list(df.sample_sets.values()))
    fs_samples_pd['Final'] = 'never_set'
    fs_samples_pd.to_csv(fs_samples_tsv_loc, sep='\t', index = False)

    return True

def samples_to_pd(samples):
    meta_df = pd.DataFrame(columns=['fs_name', 'df', 'preproc', 'size', 'bytes', 'reads','bps'])
    for s in samples:
        meta_df.loc[s['sample']]=[s['fs_name'], s['df'], s['preproc'], s['size'], s['bytes'], s['reads'],s['bps']]
    return meta_df.sort_values('fs_name')



