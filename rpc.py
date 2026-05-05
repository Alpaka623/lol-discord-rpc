import os
import time
import json
import urllib3
import requests
from pypresence import Presence
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration from .env
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1500480929087623318")
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")
LOCKFILE_PATH_ENV = os.getenv("LEAGUE_LOCKFILE_PATH")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))
PROFILE_LINK_LOL = os.getenv("PROFILE_LINK_LOL")
PROFILE_LINK_TFT = os.getenv("PROFILE_LINK_TFT")

# Default GIF URLs
GIF_URL_DEFAULT = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2NhMHl5NDNubGIza2RtN3MyM2ZreXExeHdhZGs0eWJ2d2Rma2VvdCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/E8NWgcqD2WUsEcoOm0/giphy.gif"
GIF_URL_TFT = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExMDNjeXZ6dnVreTlnc3F6NmIwc2Yzanh6cDQ1bDYxZm9yeGt4ZTk0aiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/a6kKC8iEBkPWBwRhd2/giphy.gif"

QUEUE_NAMES = {
    "RANKED_TFT_DOUBLE_UP": "TFT - Double Up",
    "RANKED_TFT_PAIRS": "TFT - Double Up",
    "RANKED_TFT": "TFT - Ranked",
    "NORMAL_TFT": "TFT - Normal",
    "RANKED_FLEX_SR": "League - Flex",
    "RANKED_SOLO_5x5": "League - Solo/Duo",
    "NORMAL_5x5_BLIND": "League - Normal (Blind)",
    "NORMAL_5x5_DRAFT": "League - Normal (Draft)",
    "ARAM_UNRANKED_5x5": "League - ARAM",
}

PHASE_MAPPING = {
    "Lobby": "In Lobby",
    "Matchmaking": "In Queue",
    "ReadyCheck": "In Queue",
    "ChampSelect": "In Champion Select",
    "InProgress": "In Game",
    "WaitingForStats": "In Menus",
    "PreEndGame": "In Menus",
    "EndOfGame": "In Menus",
    "WatchInProgress": "Spectating",
}

_champion_map = {}
_gif_cache = {}

def find_lockfile():
    """Try to find the League of Legends lockfile."""
    if LOCKFILE_PATH_ENV and os.path.exists(LOCKFILE_PATH_ENV):
        return LOCKFILE_PATH_ENV
    
    # Common installation paths
    common_paths = [
        r"C:\Riot Games\League of Legends\lockfile",
        r"D:\Spiele\Riot Games\League of Legends\lockfile",
        r"C:\Program Files\Riot Games\League of Legends\lockfile",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
            
    return None

def get_lockfile_data():
    path = find_lockfile()
    if not path or not os.path.exists(path):
        return None, None
    try:
        with open(path, "r") as f:
            parts = f.read().split(":")
            if len(parts) >= 4:
                return parts[2], parts[3]
    except Exception:
        pass
    return None, None


def get_gameflow_phase(port, password):
    try:
        resp = requests.get(
            f"https://127.0.0.1:{port}/lol-gameflow/v1/gameflow-phase",
            auth=("riot", password), verify=False, timeout=2,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def load_champion_map():
    global _champion_map
    if _champion_map:
        return
    try:
        version_resp = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json", timeout=5
        )
        version = version_resp.json()[0]
        data = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json",
            timeout=5,
        ).json()
        _champion_map = {int(v["key"]): v["name"] for v in data["data"].values()}
        print(f"Champion-Daten geladen ({len(_champion_map)} Champions)")
    except Exception as e:
        print(f"Champion-Daten konnten nicht geladen werden: {e}")


def get_champion_gif(champion_name):
    if not GIPHY_API_KEY:
        return None
        
    if champion_name in _gif_cache:
        return _gif_cache[champion_name]
    try:
        resp = requests.get(
            "https://api.giphy.com/v1/gifs/search",
            params={"api_key": GIPHY_API_KEY, "q": f"{champion_name} league of legends", "limit": 1, "rating": "g"},
            timeout=5,
        )
        gifs = resp.json().get("data", [])
        if gifs:
            gif_url = f"https://media.giphy.com/media/{gifs[0]['id']}/giphy.gif"
            _gif_cache[champion_name] = gif_url
            print(f"GIF gefunden für {champion_name}: {gif_url}")
            return gif_url
    except Exception as e:
        print(f"Giphy-Fehler für {champion_name}: {e}")
    return None


def get_champion_name_ingame(riot_id):
    try:
        resp = requests.get(
            "https://127.0.0.1:2999/liveclientdata/allgamedata",
            verify=False, timeout=3,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        active_riot_id = data.get("activePlayer", {}).get("riotId", "")
        for player in data.get("allPlayers", []):
            if player.get("riotId", "") == active_riot_id:
                return player.get("championName")
    except Exception:
        pass
    return None


def get_current_champion(port, password):
    try:
        resp = requests.get(
            f"https://127.0.0.1:{port}/lol-champ-select/v1/current-champion",
            auth=("riot", password), verify=False, timeout=5,
        )
        if resp.status_code == 200:
            champion_id = resp.json()
            if champion_id and champion_id > 0:
                return champion_id
    except Exception:
        pass
    try:
        resp = requests.get(
            f"https://127.0.0.1:{port}/lol-champ-select/v1/session",
            auth=("riot", password), verify=False, timeout=5,
        )
        if resp.status_code == 200:
            session = resp.json()
            local_cell = session.get("localPlayerCellId", -1)
            for player in session.get("myTeam", []):
                if player.get("cellId") == local_cell:
                    return player.get("championId", 0)
    except Exception:
        pass
    return 0


def get_game_name(lol):
    queue_type = lol.get("gameQueueType", "")
    game_mode = lol.get("gameMode", "")
    if queue_type in QUEUE_NAMES:
        return QUEUE_NAMES[queue_type]
    if game_mode == "TFT":
        return "TFT"
    return "League of Legends"


def is_tft(lol):
    queue_type = lol.get("gameQueueType", "")
    game_mode = lol.get("gameMode", "")
    return "TFT" in queue_type or game_mode == "TFT"


def get_ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix


def get_tft_stats(riot_id, tagline, port, password, double_up=False):
    try:
        resp = requests.get(
            "https://127.0.0.1:2999/liveclientdata/allgamedata",
            verify=False, timeout=3,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        players = data.get("allPlayers", [])
        active_player_data = data.get("activePlayer", {})
        
        if not players:
            return None

        active_riot_id = active_player_data.get("riotId")
        user_player = None
        if active_riot_id:
            for p in players:
                if p.get("riotId") == active_riot_id:
                    user_player = p
                    break
        
        if not user_player:
            full_id = f"{riot_id}#{tagline}" if tagline else riot_id
            for p in players:
                p_riot_id = p.get("riotId", "")
                p_summoner_name = p.get("summonerName", "")
                if (p_riot_id == full_id or 
                    p_riot_id == riot_id or 
                    p_summoner_name == riot_id or 
                    p_riot_id.startswith(f"{riot_id}#")):
                    user_player = p
                    break
        
        if not user_player:
            return None

        lvl = int(user_player.get("level", 1))
        gold = int(active_player_data.get("currentGold", 0))
        stats_line = f"Lvl {lvl} • {gold}g"
        
        total_players = len(players)
        team_size = 2 if double_up else 1
        total_teams = total_players // team_size
        
        if user_player.get("isDead", False):
            events = data.get("events", {}).get("Events", [])
            eliminated_names = []
            for e in events:
                if e.get("EventName") == "ChampionKill" and e.get("KillerName") == e.get("VictimName"):
                    v = e.get("VictimName")
                    if v not in eliminated_names:
                        eliminated_names.append(v)
            
            user_name_in_list = user_player.get("riotId") or user_player.get("summonerName")
            
            try:
                idx = eliminated_names.index(user_name_in_list)
                placement = total_teams - idx
            except:
                placement = sum(1 for p in players if not p.get("isDead", False)) + 1
            
            return f"Eliminated ({get_ordinal(placement)})"
        else:
            alive_count = sum(1 for p in players if not p.get("isDead", False))
            alive_teams = alive_count // team_size
            
            if alive_teams == 1:
                state = "Won"
            elif alive_teams <= 3:
                state = f"Top {alive_teams}"
            else:
                state = f"{alive_teams} Players left"
            
            return f"{state} ({stats_line})"
    except Exception:
        pass
    return None


def get_live_kda():
    try:
        resp = requests.get(
            "https://127.0.0.1:2999/liveclientdata/allgamedata",
            verify=False, timeout=3,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        active = data.get("activePlayer", {})
        riot_id = active.get("riotId", "") or active.get("summonerName", "")
        for player in data.get("allPlayers", []):
            if player.get("riotId", "") == riot_id or player.get("summonerName", "") == riot_id:
                scores = player.get("scores", {})
                k = int(scores.get("kills", 0))
                d = int(scores.get("deaths", 0))
                a = int(scores.get("assists", 0))
                return f"{k}/{d}/{a}"
    except Exception as e:
        print(f"KDA API Fehler: {e}")
    return None


def get_state(game_status, gameflow_phase=None):
    if gameflow_phase and gameflow_phase in PHASE_MAPPING:
        return PHASE_MAPPING[gameflow_phase]
        
    status = game_status.lower()
    if "ingame" in status or "in_game" in status:
        return "In Game"
    if "champ" in status or "champion" in status:
        return "In Champion Select"
    if "inqueue" in status or "in_queue" in status or "searching" in status:
        return "In Queue"
    if "hosting" in status or "lobby" in status:
        return "In Lobby"
    return "In Menus"


def make_rpc():
    rpc = Presence(CLIENT_ID, pipe=0)
    rpc.connect()
    return rpc


def main():
    load_champion_map()
    rpc = make_rpc()
    print("Mit Discord verbunden. Warte auf League Client...")

    current_champion_gif = None
    last_champion_id = 0
    game_start_time = None
    last_state = None

    while True:
        port, password = get_lockfile_data()
        if not port:
            current_champion_gif = None
            last_champion_id = 0
            time.sleep(POLL_INTERVAL)
            continue

        try:
            url = f"https://127.0.0.1:{port}/lol-chat/v1/me"
            resp = requests.get(url, auth=("riot", password), verify=False, timeout=5)
            if not resp.content:
                time.sleep(POLL_INTERVAL)
                continue
            
            data = resp.json()
            riot_name = data.get("gameName", "")
            tagline = data.get("tagLine", "")
            
            lol = data.get("lol", {})
            game_status = lol.get("gameStatus", "")
            
            gameflow_phase = get_gameflow_phase(port, password)
            state_text = get_state(game_status, gameflow_phase)
            
            game_name = get_game_name(lol)
            tft = is_tft(lol)

            current_champion_name = None
            details_text = game_name

            if tft:
                gif = GIF_URL_TFT
            elif state_text in ("In Champion Select", "In Game"):
                if state_text == "In Game":
                    champion_name_live = get_champion_name_ingame(riot_name)
                    if champion_name_live and champion_name_live != current_champion_name:
                        current_champion_name = champion_name_live
                        found = get_champion_gif(champion_name_live)
                        current_champion_gif = found if found else GIF_URL_DEFAULT
                    details_text = current_champion_name or game_name
                else:
                    champion_id = get_current_champion(port, password)
                    if champion_id and champion_id != last_champion_id:
                        last_champion_id = champion_id
                        champion_name = _champion_map.get(champion_id)
                        if champion_name:
                            found = get_champion_gif(champion_name)
                            current_champion_gif = found if found else GIF_URL_DEFAULT
                            current_champion_name = champion_name
                        else:
                            current_champion_gif = GIF_URL_DEFAULT
                    
                    if current_champion_name:
                        details_text = f"Hovering: {current_champion_name}"
                    else:
                        details_text = game_name
                gif = current_champion_gif or GIF_URL_DEFAULT
            else:
                current_champion_gif = None
                current_champion_name = None
                last_champion_id = 0
                gif = GIF_URL_DEFAULT

            if state_text != last_state:
                last_state = state_text
                if state_text == "In Game":
                    game_start_time = int(time.time())
                elif state_text not in ("In Champion Select", "In Game"):
                    game_start_time = None

            if state_text == "In Game":
                if tft:
                    double_up = lol.get("gameQueueType", "") in ("RANKED_TFT_DOUBLE_UP", "RANKED_TFT_PAIRS")
                    stats = get_tft_stats(riot_name, tagline, port, password, double_up=double_up)
                    display_state = f"In Game • {stats}" if stats else "In Game"
                else:
                    kda = get_live_kda()
                    display_state = f"In Game • {kda}" if kda else "In Game"
            else:
                display_state = state_text

            # Buttons logic
            buttons = []
            if PROFILE_LINK_LOL:
                buttons.append({"label": "u.gg Profile", "url": PROFILE_LINK_LOL})
            if PROFILE_LINK_TFT:
                buttons.append({"label": "MetaTFT Profile", "url": PROFILE_LINK_TFT})

            kwargs = {
                "state": display_state,
                "details": details_text,
                "large_image": gif,
                "large_text": riot_name,
                "start": game_start_time,
            }
            
            if buttons:
                kwargs["buttons"] = buttons

            if state_text == "In Lobby":
                pty_raw = lol.get("pty", "{}")
                pty = json.loads(pty_raw)
                current = len(pty.get("summoners", []))
                maximum = pty.get("maxPlayers", 5)
                kwargs["party_size"] = [current, maximum]

            rpc.update(**kwargs)
            print(f"Status: {state_text} | {game_name}")
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"League API nicht erreichbar: {e}")
        except Exception as e:
            print(f"Discord-Fehler: {e} — verbinde neu...")
            try:
                rpc.close()
            except Exception:
                pass
            try:
                rpc = make_rpc()
            except Exception:
                pass

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
