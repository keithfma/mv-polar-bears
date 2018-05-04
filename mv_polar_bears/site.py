"""
Build static webpage exploring MV Polar Bears dataset
"""

from bokeh import plotting as bk_plt
from bokeh import models as bk_model
from bokeh import embed as bk_embed
import jinja2

# plot format constants
GROUP_COLOR = 'royalblue'
NEWBIES_COLOR = 'forestgreen'
FONT_SIZE = '20pt'
DAY_TO_MSEC = 60*60*24*1000

# webpage constants
WEBPAGE_TITLE = 'MV Polar Bears!'
PUBLISH_DIR = 'docs'

def add_dates(data):
    """
    Convert year, month, day columns to datetime.date objects

    Return: Nothing, adds "DATE" column to dataframe
    """
    data['DATE'] = pd.to_datetime(data[['YEAR', 'MONTH', 'DAY']]).dt.date
    data.set_index(pd.to_datetime(data[['YEAR', 'MONTH', 'DAY']]), inplace=True)


def set_font_size(fig):
    """Update font sizes in input Bokeh figures"""
    fig.title.text_font_size = FONT_SIZE
    fig.xaxis.axis_label_text_font_size = FONT_SIZE
    fig.yaxis.axis_label_text_font_size = FONT_SIZE
    fig.xaxis.major_label_text_font_size = FONT_SIZE
    fig.yaxis.major_label_text_font_size = FONT_SIZE
    fig.legend.label_text_font_size = FONT_SIZE


def set_ylabel_to_positive(fig):
    """Replace negative-valued y labels with thier absolute value"""
    fig.yaxis.formatter = bk_model.FuncTickFormatter(code="return Math.abs(tick)")


def daily_bar_plot(data):
    """
    Arguments:
        data: pandas dataframe

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
    # create figure
    fig = bk_plt.figure(
        title="Daily Attendence",
        x_axis_label='Date',
        x_axis_type='datetime',
        y_axis_label='# Attendees',
        plot_width=1700,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )
    
    # add bar plots
    fig.vbar(
        x=data['DATE'], width=DAY_TO_MSEC, bottom=0, top=data['GROUP'],
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=data['DATE'], width=DAY_TO_MSEC, bottom=-data['NEWBIES'], top=0,
        color=NEWBIES_COLOR, legend='Newbies')

    # additional formatting
    set_font_size(fig)
    set_ylabel_to_positive(fig)

    return bk_embed.components(fig)


def weekly_bar_plot(data):
    """
    Arguments:
        data: pandas dataframe

    Returns: script, div
        script: javascript function controlling plot, wrapped in <script> HTML tags
        div: HTML <div> modified by javascript to show plot
    """
    # compute weekly sums
    weekly = data[['GROUP', 'NEWBIES']].resample('W').sum()

    # create figure
    fig = bk_plt.figure(
        title="Weekly Attendence",
        x_axis_label='Week Start Date',
        x_axis_type='datetime',
        y_axis_label='Total # Attendees',
        plot_width=1700,
        tools="pan,wheel_zoom,box_zoom,reset",
        logo=None
        )
    
    # add bar plots
    fig.vbar(
        x=weekly.index, width=DAY_TO_MSEC*7, bottom=0, top=weekly['GROUP'],
        color=GROUP_COLOR, legend='Group')
    fig.vbar(
        x=weekly.index, width=DAY_TO_MSEC*7, bottom=-weekly['NEWBIES'], top=0,
        color=NEWBIES_COLOR, legend='Newbies')

    # additional formatting
    set_font_size(fig)
    set_ylabel_to_positive(fig)

    return bk_embed.components(fig)


def resample_to_daily(data):
    """Resample input dataframe to daily resolution (initial cleaning step)"""
    lookup_day = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    data = data.resample('D').mean() # daily frequency, no gaps
    data['DATE'] = pd.Series(
        {x: x.to_pydatetime().date() for x in data.index})
    data['YEAR'] = data['DATE'].apply(lambda x: x.year)
    data['MONTH'] = data['DATE'].apply(lambda x: x.month)
    data['DAY'] = data['DATE'].apply(lambda x: x.day)
    data['DAY-OF-WEEK'] = data['DATE'].apply(lambda x: lookup_day[x.weekday()])
    data.set_index('DATE', drop=False, inplace=True)
    return data


def get_table_data(data):
    """
    Munge data to build a daily view of all available data
    
    Arguments:
        data: pandas dataframe

    Returns:
        list of dicts, each containing data for a single day, with no gaps
    """
    table_data = data.replace(nan, '-')
    table_dict = table_data.T.to_dict()
    table = []
    for date in sorted(table_data['DATE']):
        table.append(table_dict[date])
    table.sort(key=lambda x: x['DATE'], reverse=True)
    return table


def build_site():
    """Get/update data and build static HTML / JS site"""

    data = sheets_read_data()
    add_dates(data)
    data = resample_to_daily(data)
    
    daily_bar_script, daily_bar_div = daily_bar_plot(data)
    weekly_bar_script, weekly_bar_div = weekly_bar_plot(data)
    daily_table = get_table_data(data)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('templates'),
        autoescape=jinja2.select_autoescape(['html', 'css'])
        )

    index_template = env.get_template('index.html')
    with open(os.path.join(PUBLISH_DIR, 'index.html'), 'w') as index_fp:
        index_content = index_template.render(
            title=WEBPAGE_TITLE,
            daily_table=daily_table,
            daily_bar_div=daily_bar_div,
            daily_bar_script=daily_bar_script,
            weekly_bar_div=weekly_bar_div,
            weekly_bar_script=weekly_bar_script
            )
        index_fp.write(index_content)

    style_template = env.get_template('style.css')
    with open(os.path.join(PUBLISH_DIR, 'style.css'), 'w') as style_fp:
        style_content = style_template.render()
        style_fp.write(style_content)
