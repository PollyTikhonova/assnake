import assnake.api.loaders
import assnake
from tabulate import tabulate
import click, os, datetime
import pandas as pd


def generic_command_dict_of_sample_sets(config, df, preproc, meta_column, column_value, samples_to_add, exclude_samples, **kwargs):
    '''
    This returns several sample sets.
    '''
    df_loaded = assnake.Dataset(df)
    
    sample_sets_dict = {}

    meta_loc = os.path.join(df_loaded.full_path, 'df_samples.tsv')
    if os.path.isfile(meta_loc):
        meta = pd.read_csv(meta_loc, sep = '\t', index_col=0)
        if meta_column is not None:
            if column_value is not None:
                sample_set, sample_set_name = generic_command_individual_samples(config,  df, preproc, meta_column, column_value, samples_to_add, exclude_samples, **kwargs)
                sample_sets_dict.update({sample_set_name: sample_set})
            else: # treat empty column_value as creating multiple sample_sets for each column_value
                column_values = list(meta[meta_column].unique())
                for column_value in column_values:
                    sample_set, sample_set_name = generic_command_individual_samples(config,  df, preproc, meta_column, column_value, samples_to_add, exclude_samples, **kwargs)
                    sample_sets_dict.update({sample_set_name: sample_set})
        else:
            sample_set, sample_set_name = generic_command_individual_samples(config,  df, preproc, meta_column, column_value, samples_to_add, exclude_samples, **kwargs)
            sample_sets_dict.update({sample_set_name: sample_set})
    else:
        if meta_column is not None:
            click.echo('A metadata column is specified, but there is no metadata file: %s'%meta_loc, fg='red')
            exit()
        sample_set, sample_set_name = generic_command_individual_samples(config,  df, preproc, meta_column, column_value, samples_to_add, exclude_samples, **kwargs)
        sample_sets_dict.update({sample_set_name: sample_set})

    return sample_sets_dict

def generic_command_individual_samples(config, df, preproc, meta_column, column_value, samples_to_add, exclude_samples, **kwargs):
    """
    Construct sample sets, has multiple options.
    Returns dict or sample_sets based on the provided options.
    
    meta_column - factor column in sample metadata sheet. Cannot be combined with samples_to_add. exclude_samples has higher proirity. 
    column_value - value of column to select by. \
        Can be multiple - separated by commas without whitespace. \
        If meta_column is provided, bot no column_value is provided \
        - treat it like select all unique values of that column. 
        If multiple - one value - one sample_set. If --merge enabled - all values go in one sample_set

    assnake result request megahit -d FMT_FHM -c source run 

    """
    exclude_samples = [] if exclude_samples == '' else [c.strip() for c in exclude_samples.split(',')]
    samples_to_add = [] if samples_to_add == '' else [c.strip() for c in samples_to_add.split(',')]

    df_loaded = assnake.Dataset(df)
    config['requested_dfs'] += [df_loaded.df]
     
    # Now for the meta column stuff
    meta_loc = os.path.join(df_loaded.full_path, 'df_samples.tsv')
    if os.path.isfile(meta_loc):
        meta = pd.read_csv(meta_loc, sep = '\t', index_col=0)
        if meta_column is not None:
            if column_value is not None:
                subset_by_col_value = meta.loc[meta[meta_column] == column_value]
                if len(subset_by_col_value) > 0:
                    samples_to_add = list(subset_by_col_value.index.values)
                    samples_to_add = list(set(df_loaded.sample_containers['df_sample'].values).intersection(set(samples_to_add)))
                    if len(samples_to_add) == 0:
                        click.secho('There are 0 samples for %s == %s'%(meta_column, column_value), fg='red')
                        exit()

    if preproc is None:
        # LONGEST
        preproc = max(list(df_loaded.sample_sets.keys()), key=len)
        click.echo('Preprocessing is not specified, using longest for now - %s'%preproc)

    sample_set = assnake.api.loaders.load_sample_set(config['wc_config'], df_loaded.fs_prefix, df_loaded.df, preproc, samples_to_add=samples_to_add)
    if len(exclude_samples) > 0 :  
        sample_set = sample_set.loc[~sample_set['df_sample'].isin(exclude_samples), ]

    # click.echo(tabulate(sample_set[['df_sample', 'reads', 'preproc']].sort_values('reads'), headers='keys', tablefmt='fancy_grid'))

    # construct sample set name for fs
    def_name = kwargs.pop('timepoint', None)
    if def_name is None:
        curr_date = datetime.datetime.now()
        def_name = '{date}{month}{year}_{hour}{minute}%s'.format(
                                date=curr_date.strftime("%d"), 
                                month=curr_date.strftime("%b"), 
                                year=curr_date.strftime("%y"),
                                hour=curr_date.strftime("%H"),
                                minute=curr_date.strftime("%M"))
    else:
        def_name = '{def_name}%s'.format(def_name=def_name)
    if meta_column is None and column_value is None:        
        sample_set_name = def_name%('')
    elif meta_column is not None and column_value is None:
        sample_set_name = def_name%('__' + meta_column)
    else:
        sample_set_name = def_name%('__' + meta_column + '_' + column_value)

    return sample_set, sample_set_name
    

def generate_result_list(sample_set, wc_str, **kwargs):
    res_list = []
    # print(kwargs)
    kwargs.pop('df')
    kwargs.pop('preproc')
    for s in sample_set.to_dict(orient='records'):
        preprocessing = s['preproc']

        res_list.append(wc_str.format(
            fs_prefix = s['fs_prefix'].rstrip('\/'),    
            df = s['df'],
            preproc = preprocessing,
            df_sample = s['df_sample'],
            **kwargs
        ))
    return res_list

def prepare_sample_set_tsv_and_get_results(sample_set_dir_wc, result_wc, df, sample_sets, overwrite,**kwargs):
    res_list = []
    destroy_if_not_run = {'directories':[], 'files':[]}

    df_loaded = assnake.Dataset(df)

    for sample_set_name in sample_sets.keys():
        sample_set_dir = sample_set_dir_wc.format(fs_prefix = df_loaded.fs_prefix, df = df, sample_set = sample_set_name)
        sample_set_loc = os.path.join(sample_set_dir, 'sample_set.tsv')


        sample_set = sample_sets[sample_set_name]
        if not os.path.exists(sample_set_dir):
            os.makedirs(sample_set_dir, exist_ok=True)
            destroy_if_not_run['directories'].append(sample_set_dir)


        if not os.path.isfile(sample_set_loc):
            sample_set.to_csv(sample_set_loc, sep='\t', index=False)
            destroy_if_not_run['files'].append(sample_set_loc)
        else:
            click.secho('Sample set with this name already exists!')
            if overwrite:
                sample_set.to_csv(sample_set_loc, sep='\t', index=False)
                click.secho('Overwritten')

        
        res_list += [result_wc.format(
            fs_prefix = df_loaded.fs_prefix,
            df = df_loaded.df,
            sample_set = sample_set_name,
            **kwargs
        )]

    return res_list, destroy_if_not_run