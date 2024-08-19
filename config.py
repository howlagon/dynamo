import json, asyncio

async def generate_config_py():
    global params
    threaded = input('Would you like to run threads? (Used for a fancy loading bar) (Y/n) ')
    flush_prints = input('Would you like each loading statement to be on a new line? (y/N) ')
    detailed = input('Would you like to see detailed step output? (y/N) ')
    # freaky = input('Are you a 𝒻𝓇𝑒𝒶𝓀? (y/N) ') # option removed v0.1.0, still available by manually editing config

    data = {
        'refresh': 60,
        'threaded': True if threaded.lower() == 'y' or threaded == '' else False,
        'flush_prints': True if flush_prints.lower() == 'y' else False if flush_prints == '' else False,
        'detailed': True if detailed.lower() == 'y' else False if detailed == '' else False,
        'freaky': False
    }

    with open('config.json', 'w') as fp:
        json.dump(data, fp, indent=4)
    
    params = data

try:
    params = json.load(open('config.json'))
except FileNotFoundError:
    params = {
        'refresh': 60,
        'threaded': True,
        'flush_prints': False,
        'detailed': False,
        'freaky': False
    }