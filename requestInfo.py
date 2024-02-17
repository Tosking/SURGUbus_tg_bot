import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
s = requests.session()

animationData = {"t":"11111111-50b3-4fec-b922-8a50a1d38366",
"ct":26,"cd":"getVehiclesAnimation.php",
"reg":86002,
"data":{"wuid":531157333272,"rids":"32,201,209,211,213,219,221,223,225,227,229,231,241,246,283,289,300,322,465,466,468,470,472,474,476,478,480,482,484,488,490,492,494,497,499,500","curk":0}}

forecastUrl = 'https://bus.admsurgut.ru/php/apiRequest.php?getVehicleForecasts.php'
animationUrl = 'https://bus.admsurgut.ru/php/apiRequest.php?getVehicleForecasts.php'
routesUrl = 'https://bus.admsurgut.ru/php/apiRequest.php?getRoutes.php'

forecastData = {"t":"11111111-50b3-4fec-b922-8a50a1d38366","ct":26,"cd":"getVehicleForecasts.php","reg":86002,"data":{"wuid":363336604752,"deviceCode":"138057305"}}
routesData = {"t":"11111111-50b3-4fec-b922-8a50a1d38366","ct":26,"cd":"getRoutes.php","reg":86002,"w":-1,"data":{"wuid":363336604752,"q":""}}

def getAllRoutes():
    query = json.loads(s.post(routesUrl, data=json.dumps(routesData), verify=False).content)
    result = [{key: d[key] for key in ['number', 'id'] if key in d} for d in query['data']]
    return result

def getIdsOfRoute(number):
    routes = getAllRoutes()
    routeId = [i for i in routes if i['number'] == number][0]
    data = animationData
    data['rids'] = str(routeId['id'])
    query = json.loads(s.post(animationUrl, data=json.dumps(data), verify=False).content)
    result = [{key: d[key] for key in ['deviceCode', 'rnum'] if key in d}['deviceCode'] for d in query['data']['anims'] if d['rnum'] == number]
    return result

def getForecasts(id):
    data = forecastData
    data['data']['deviceCode'] = id
    query = json.loads(s.post(forecastUrl, data=json.dumps(data), verify=False).content)
    result = [{key: d[key] for key in ['arrt', 'stname', 'stdescr'] if key in d} for d in query['data']]
    return result
