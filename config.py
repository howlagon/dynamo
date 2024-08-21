import json, asyncio

async def generate_config_py():
    global params
    flush_prints = input('Would you like each loading statement to be on a new line? (y/N) ')
    detailed = input('Would you like to see detailed step output? (y/N) ')
    # freaky = input('Are you a 𝒻𝓇𝑒𝒶𝓀? (y/N) ') # option removed v0.1.0, still available by manually editing config

    data = {
        'flush_prints': True if flush_prints.lower() == 'y' else False if flush_prints == '' else False,
        'detailed': True if detailed.lower() == 'y' else False if detailed == '' else False,
        'freaky': False,
        'headless': False
    }

    with open('config.json', 'w') as fp:
        json.dump(data, fp, indent=4)
    
    params = data

try:
    params = json.load(open('config.json'))
except FileNotFoundError:
    params = {
        'flush_prints': False,
        'detailed': False,
        'freaky': False,
        'headless': False
    }

params['refresh'] = 300
params['threaded'] = True
params['testrun'] = False
params['print_end'] = ''