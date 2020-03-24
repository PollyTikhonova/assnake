import assnake.api.loaders
import assnake
from tabulate import tabulate
import click, os, datetime
import pandas as pd

# https://stackoverflow.com/a/40195800
sample_set_construction_options = []

sample_set_construction_options = [
    click.option('--df','-d', help='Name of the dataset', required=True ),
    click.option('--preproc','-p', help='Preprocessing to use' ),

    click.option('--meta-column', '-c', help='Select samples based on metadata column' ),
    click.option('--column-value','-v', help='Value of metadata column by which select samples' ),

    click.option('--samples-to-add','-s', 
                help='Samples from dataset to process', 
                default='', 
                metavar='<samples_to_add>', 
                type=click.STRING ),
    click.option('--exclude-samples','-x', 
                help='Exclude this samples from run', 
                default='', 
                metavar='<samples_to_add>', 
                type=click.STRING ),
]

options_w_params = [
    click.option('--df','-d', help='Name of the dataset', required=True ),
    click.option('--preproc','-p', help='Preprocessing to use' ),

    click.option('--meta-column', '-c', help='Select samples based on metadata column' ),
    click.option('--column-value','-v', help='Value of metadata column by which select samples' ),

    click.option('--samples-to-add','-s', 
                help='Samples from dataset to process', 
                default='', 
                metavar='<samples_to_add>', 
                type=click.STRING ),
    click.option('--exclude-samples','-x', 
                help='Exclude this samples from run', 
                default='', 
                metavar='<samples_to_add>', 
                type=click.STRING ),
    click.option('--params', 
                help='Parameters to use', 
                default='def',
                type=click.STRING )
]


def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options


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

    df_loaded = assnake.api.loaders.load_df_from_db(df)
    config['requested_dfs'] += [df_loaded['df']]

    # Now for the meta column stuff
    meta_loc = os.path.join(df_loaded['fs_prefix'], df_loaded['df'], 'mg_samples.tsv')
    if os.path.isfile(meta_loc):
        meta = pd.read_csv(meta_loc, sep = '\t')
        if meta_column is not None:
            if column_value is not None:
                subset_by_col_value = meta.loc[meta[meta_column] == column_value]
                if len(subset_by_col_value) > 0:
                    samples_to_add = list(subset_by_col_value['sample_name'])



    sample_set = assnake.SampleSet(df_loaded['fs_prefix'], df_loaded['df'], preproc, samples_to_add=samples_to_add)
    if len(exclude_samples) > 0 :  
        sample_set.samples_pd = sample_set.samples_pd.loc[~sample_set.samples_pd['fs_name'].isin(exclude_samples), ]

    click.echo(tabulate(sample_set.samples_pd[['fs_name', 'reads', 'preproc']].sort_values('reads'), headers='keys', tablefmt='fancy_grid'))

    # construct sample set name for fs
    if meta_column is None and column_value is None:
        curr_date = datetime.datetime.now()
        def_name = '{month}{year}'.format(month=curr_date.strftime("%b"), year=curr_date.strftime("%y"))
        sample_set_name = def_name
    else:
        sample_set_name = meta_column + '__' + column_value

    return sample_set, sample_set_name
    

def generate_result_list(sample_set, wc_str, df, preproc, meta_column, column_value, samples_to_add, exclude_samples, **kwargs):
    res_list = []
    for s in sample_set.samples_pd.to_dict(orient='records'):
        preprocessing = s['preproc']
        res_list.append(wc_str.format(
            fs_prefix = s['fs_prefix'].rstrip('\/'),    
            df = s['df'],
            preproc = preprocessing,
            sample = s['fs_name'],
            **kwargs
        ))
    return res_list

# def magic_options(func):
#     @add_options(options)
#     @click.pass_obj
#     def distill_magic(config, **kwargs):
#         kwargs['result'] = 'ssss'
#         func(config, **kwargs)

#     return distill_magic

# @click.command('test')
# @magic_options
# def tt(config, **kwargs):
#     print(kwargs)