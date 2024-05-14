import sys
import configparser

def load_config():
    config = configparser.ConfigParser()
    config.read('yaffle.ini')

    if('Yaffle' not in config):
        print("Failed to load config file")
        create_initial_config()
        config.read('yaffle.ini')
        if(config is None):
            print("Failed to load config file")
            sys.exit(1)
        else:
            load_config()
    else:
        if 'Yaffle' in config:
            return config['Yaffle']

def create_initial_config():
    config = configparser.ConfigParser()
    config['Yaffle'] = {'YARR_URL': 'http://127.0.0.1:7070'}
    with open('yaffle.ini', 'w', encoding='utf-8') as configfile:
        config.write(configfile)

def save_config(frame):
    try:
        config = configparser.ConfigParser()
        config.read('yaffle.ini')
        config['Yaffle']['selected_feed'] = str(frame.feed_tree.GetItemData(frame.feed_tree.GetSelection()))
        with open('yaffle.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    except:
        print("Failed to save state")
        return