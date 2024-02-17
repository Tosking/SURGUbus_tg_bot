import os
import json

statsFile = 'stats.json'
if not os.path.exists(statsFile):
    stats = {
        'notifyings': 0,
        'button_clicks' : 0
    }
    with open(statsFile, 'w') as f:
        json.dump(stats, f)

def addNotifyings():
    with open(statsFile, 'r') as f:
        stats = json.load(f)
        stats['notifyings'] += 1

    with open(statsFile, 'w') as f:
        json.dump(stats, f)

def addButtonClicks():
    with open(statsFile, 'r') as f:
        stats = json.load(f)
        stats['button_clicks'] += 1

    with open(statsFile, 'w') as f:
        json.dump(stats, f)
