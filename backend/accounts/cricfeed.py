import os
import urllib.request
import json
import re
from datetime import datetime, timezone

CRIC_API_KEY = os.environ.get('CRIC_API_KEY')
CRIC_TOURNAMENT_ID = os.environ.get('CRIC_TOURNAMENT_ID')


# method with optional parameter tournament id
def get_series_info(tournament_id=None):
    if tournament_id is None:
        tournament_id = CRIC_TOURNAMENT_ID
    CRIC_SERIES_INFO_URL = "https://api.cricapi.com/v1/series_info?apikey=" + CRIC_API_KEY + "&id=" + tournament_id
    # open url and save json output into a file
    # urllib.request.urlretrieve(CRIC_SERIES_INFO_URL, filename="series_info.json")

    # open url and save json output into json object
    with urllib.request.urlopen(CRIC_SERIES_INFO_URL) as url:
        data = json.loads(url.read().decode())
    #     print(data)

    # open json file into json object
    # with open('series_info.json') as json_file:
    #     data = json.load(json_file)
    out_match = []
    if 'data' not in data:
        return
    for match in data["data"]['matchList']:
        try:
            tmp_match = {}
            if match["teams"][0] == "Tbc" or match["teams"][1] == "Tbc":
                continue
            tmp_match["match_id"] = match["id"]
            tmp_match["Team1"] = match["teams"][0]
            tmp_match["Team2"] = match["teams"][1]
            # team order and team info order might be different
            # check if teaminfo value exists
            if 'teamInfo' in match:
                if tmp_match["Team1"] == match["teamInfo"][0]["name"]:
                    tmp_match["Team1Info"] = match["teamInfo"][0]
                    tmp_match["Team2Info"] = match["teamInfo"][1]
                else:
                    tmp_match["Team1Info"] = match["teamInfo"][1]
                    tmp_match["Team2Info"] = match["teamInfo"][0]
            else:
                tmp_match["Team1Info"] = {}
                tmp_match["Team2Info"] = {}
                tmp_match["Team1Info"]["name"] = match["teams"][0]
                tmp_match["Team2Info"]["name"] = match["teams"][1]
                tmp_match["Team1Info"]["shortname"] = ""
                tmp_match["Team2Info"]["shortname"] = ""
                tmp_match["Team1Info"]["img"] = ""
                tmp_match["Team2Info"]["img"] = ""
            #count comma in match name
            tmp=(match["name"].count(','))*-1
            tmp_match["Description"] = match["name"].split(",")[tmp].strip()
            tmp_match["venue"] = match["venue"].split(",")[-1].strip()
            tmp_match["datetime"] = match["dateTimeGMT"]
            tmp_match["tournament"] = tournament_id
            if match["status"] == "Match not started":
                tmp_match["result"] = "TBD"
            elif "won" in match["status"] and match["matchEnded"] == True:
                if tmp_match["Team1"] in match["status"]:
                    tmp_match["result"] = "team1"
                elif tmp_match["Team2"] in match["status"]:
                    tmp_match["result"] = "team2"
            else:
                tmp_match["result"] = "NR"
            print(tmp_match)
            out_match.append(tmp_match)
        except Exception as error:
            print("Error in parsing match: %s", match)
            print(error)
    return out_match


def get_match_info(match_id):
    if len(match_id) < 5:
        return "ERR"
    CRIC_MATCH_INFO_URL = "https://api.cricapi.com/v1/match_info?apikey=" + CRIC_API_KEY + "&id=" + match_id
    # open url and save json output into a file
    # urllib.request.urlretrieve(CRIC_MATCH_INFO_URL, filename="match_info.json")

    # open url and save json output into json object
    with urllib.request.urlopen(CRIC_MATCH_INFO_URL) as url:
        data = json.loads(url.read().decode())

    # open json file into json object
    # with open('match_info_notstarted.json') as json_file:
    #     data = json.load(json_file)
    print(data)
    if data['status'] != 'success':
        print("API call failed")
        return "TBD"
    match_data = data['data']
    if match_data['matchStarted']:
        if match_data['matchEnded']:
            print("Match %s ended and winner is " % match_id, match_data['matchWinner'])
            return match_data['matchWinner']
        else:
            print("Match %s in progress" % match_id)
            return "IP"
    print("Match %s not started" % match_id)
    return "TBD"

# get_series_info()
# print(get_match_info('18998bfa-aabc-48e3-b73e-d15f56493fa6'))
