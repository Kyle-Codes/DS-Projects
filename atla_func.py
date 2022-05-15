from typing import Iterable, List
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud, STOPWORDS
from PIL import Image
from collections import namedtuple
import string
from venv import create
import requests
from bs4 import BeautifulSoup
import httpx 
import asyncio
import pandas as pd

color_dict = {
    'aang': 'goldenrod',
    'katara': 'deepskyblue',
    'sokka': 'dodgerblue',
    'suki': 'lightgreen',
    'toph': 'green',
    'zuko': 'red',
    'iroh': 'maroon',
    'mai': 'black',
    'ty lee': 'hotpink',
    'azula': 'orangered',
    'other': 'grey'}

def create_episode_dict(season, episode, title, character_list) -> dict:
    '''
    Returns dictionary of episode information, including season, episode, and title. 
    Also defines blank lists for all characters that will later be filled with dialogue
    '''
    
    ep_dialogue = {
                    'Season': season,
                    'Episode': episode, 
                    'Title': title,
                    'Dialogue': {char: [] for char in character_list}
                }

    return ep_dialogue

def crawl_page(url: string) -> BeautifulSoup:
    '''
    Crawls a URL and returns a BeautifulSoup type obnject of the page's HTML
    '''
    # url = f"https://avatar.fandom.com/wiki/Transcript:{episode_title}"
    page = requests.get(url)
    page_soup = BeautifulSoup(page.content, 'html.parser')
    return page_soup

def clean_square_brackets(string) -> str:
    ''' Custom function per Wiki's formatting of ATLA scripts; 
    dialogue between square brackets indicates actions, not dialogue'''
    import re
    s = string
    return re.sub(r'\[(.+?)\]', '', s)

def clean_dialogue(text) -> str:
    '''Cleans messy dialogue e.g. removes formatting keys like "\n" '''
    dialogue = clean_square_brackets(text)
    return dialogue.replace('\n', '').strip()

def get_character_dialogue(page, dialogue_dict: namedtuple, character_list:list=None, other=False) -> None:
    '''
    Parses through a page for dialogue tables and appends the values of character list inplace to dialogue_dict
    Returns: 
        None; appends dialogue inplace to dialogue_dict
    '''
    all_tables = page.body.find_all('table')
    # Note that by parsing all tables, we run the risk of overcounting some pages that include deleted scenes
    # However, the only other viable option is to hardcode tables for exceptional episodes, as some episodes (e.g. The Tales of Ba Sing Se)
    # Split their episode scripts into multiple tables, and some include a separate table for introductory screens.
    for table in all_tables:
        script = table.find_all('tr')
        for script_line in script:
            if script_line.find('th'):
                try:
                    speaker = script_line.find('th').string.lower().replace('\n', '').replace('young', '').strip()
                    if other and character_list and speaker not in character_list:
                        speaker = 'other'
                    dialogue = clean_dialogue(script_line.find('td').text)
                    # Exclude intro table dialogue (only included in some transcripts, notably episode 1 and 2)
                    if dialogue.startswith('Water. Earth. Fire. Air.'):
                        break
                    dialogue_dict['Dialogue'][speaker].append(dialogue)
                except:
                    pass

def count_words(episode_lines_list: List) -> int:
    '''Count number of individual words spoken by a character. Expects a list of words of dialogue'''
    tmp = []
    for line in episode_lines_list:
        #replace all special charcters; add to as required
        tmp.append(line.replace('-', '')) 
    return len(' '.join(tmp).split())

async def grab_htmls(urls: Iterable):
    '''Grab HTMLs for each of a list/series of URLs asynchronously '''
    async with httpx.AsyncClient() as client:
        tasks = (client.get(url) for url in urls)
        reqs = await asyncio.gather(*tasks)
    return [req.text for req in reqs]
 
def get_atla_dialogue(html, dialogue_dict: namedtuple, character_list=False, other=False) -> dict:
    page = BeautifulSoup(html, 'html.parser')
    get_character_dialogue(page, dialogue_dict, character_list, other)
    return

async def make_atla_df(episode_df, character_list, other=False):
    '''Create and return dataframe of episodic dialogue for character_list (+ aggregated "other" characters if other=True)'''
    assert 'title' in episode_df.columns.str.lower(), 'episode_df parameter missing expected "Title" column'

    urls = episode_df.Title.apply(lambda title: f"http://avatar.fandom.com/wiki/Transcript:{title}")
    htmls = await grab_htmls(urls)

    ep_info_lst = []
    for episode_num, html in enumerate(htmls):
        ep_dict = create_episode_dict(
                episode_df.Season.iloc[episode_num], 
                episode_df.Episode.iloc[episode_num], 
                episode_df.Title.iloc[episode_num],
                character_list=character_list)
        get_atla_dialogue(html, ep_dict, character_list=character_list, other=other)
        ep_info_lst.append(ep_dict)

    dialogue_df = pd.DataFrame(ep_info_lst)
    dialogue_df = dialogue_df.drop("Dialogue", axis=1).join(dialogue_df["Dialogue"].apply(pd.Series))
    return dialogue_df

def make_wordcloud(ax:plt.Axes, df, character, av_image, figsize=(10, 15), save=False):    
    """
    Create the word cloud using the word cloud library
    df: pd.DataFrame
    character: name of df column to make wordcloud for
    """
    # Change directory to image repository as required
    av_image = f"../atla files/{av_image}"

    # Compile all individual episode lists of words into a single list
    char_string = ' '.join(df[character].apply(lambda x: ' '.join(x)))
    stopwords = set(STOPWORDS)
    char_mask = np.array(Image.open(av_image))
    wc = WordCloud(
        stopwords=stopwords, 
        mask=char_mask, 
        background_color="white", 
        mode="RGBA", 
        max_words=750).generate(char_string.lower())
    ax.imshow(wc, interpolation='bilinear')
    ax.set_title(f"{character.capitalize()} Wordcloud", size = 16)
    ax.axis("off")
    if save:
        wc.to_file(f"../atla files/{character} wordcloud.png")
    return ax