import sys
import configparser

def load_config():
    config = configparser.ConfigParser()
    config.read('yaffle.ini')

    if('Yaffle' not in config):
        create_initial_config()
        config.read('yaffle.ini')
        if(config is None):
            sys.exit(1)
        else:
            load_config()
    else:
        return config['Yaffle']

def create_initial_config():
    config = configparser.ConfigParser()
    config['Yaffle'] = {'YARR_URL': 'http://127.0.0.1:7070',
                        'selected_feed': '0'}
    with open('yaffle.ini', 'w', encoding='utf-8') as configfile:
        config.write(configfile)

def save_config(frame):
    try:
        config = configparser.ConfigParser()
        config.read('yaffle.ini')
        config['Yaffle']['selected_feed'] = str(frame.feed_tree.GetItemData(frame.feed_tree.GetSelection()))

        width, height = frame.GetSize()
        config['Yaffle']['dimensions'] = f"{width}x{height}"

        x, y = frame.GetPosition()
        config['Yaffle']['position'] = f"{x},{y}"

        with open('yaffle.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    except:
        print("Failed to save state")
        return