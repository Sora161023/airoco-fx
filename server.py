import json
import datetime
import os
import sqlite3
import urllib.parse
from wsgiref.simple_server import make_server

class UserDB:
    DB_NAME    = 'users.db'
    TABLE_NAME = 'users'
    KEY_LIST   = ['log_time', 'user_name', 'score']

    # query一覧
    CREATE_TABLE = f'''
        CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
            log_time TEXT,
            user_name TEXT PRIMARY KEY,
            score INTEGER
        )
    '''
    INSERT_USER = f'''
        INSERT INTO {TABLE_NAME}(log_time, user_name, score) VALUES (?, ?, ?)
    '''                   # 新しいスコアを挿入
    UPDATE_SCORE = f'''
        UPDATE {TABLE_NAME} SET log_time = (?), score = (?) WHERE user_name = (?)
    '''
    SELECT_USER = f'''
        SELECT * FROM {TABLE_NAME} WHERE user_name = (?)
    '''
    SELECT_TOP = f'''
        SELECT * FROM {TABLE_NAME} ORDER BY score DESC LIMIT (?)
    '''
    SELECT_RANKING = f'''
        SELECT *, RANK() OVER(ORDER BY score DESC) as ranking FROM {TABLE_NAME} WHERE user_name = (?)
    '''                                           # IDで検索

    def __init__(self):
        if not os.path.isfile(self.DB_NAME):
            self._execute(self.CREATE_TABLE)

    def _execute(self, query, params=()) -> list:
        """queryを実行"""
        with sqlite3.connect(self.DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            res = cur.fetchall()

            return res
    
    def _get_log_time(self) -> str:
        """現在時刻をYYYY-MM-DD HH:MM:SSで表示"""
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def is_registered(self, user_name: str):
        if self._execute(self.SELECT_USER, [user_name]):
            return {"success": False, "message": f"Already used this name: {user_name}"}
        else:
            log_time = self._get_log_time()
            self._execute(self.INSERT_USER, [log_time, user_name, 10000])
            return {"success": True, "message": f"Registered the user: {user_name}"}

    def get_my_money(self, user_name: str):
        res = self._execute(self.SELECT_USER, [user_name])
        if res:
            return {1: dict(zip(self.KEY_LIST, res[0]))}
        return {}
    
    def set_my_money(self, user_name: str, score: int):
        log_time = self._get_log_time()
        if self._execute(self.SELECT_USER, [user_name]):
            self._execute(self.UPDATE_SCORE, [log_time, user_name, score])
        else:
            self._execute(self.INSERT_USER, [log_time, user_name, score])

    def get_top_ranking(self, limit: int):
        res = self._execute(self.SELECT_TOP, [limit])
        if res:
            return {
                i+1: dict(zip(self.KEY_LIST, row)) for i, row in enumerate(res)
            }
        return {}
    
    def get_my_ranking(self, user_name: str):
        res = self._execute(self.SELECT_RANKING, [user_name])
        if res:
            return {str(res[0][-1]): dict(zip(self.KEY_LIST, res[0]))}
        return {}



class APIServer:
    def __init__(self, host: str='localhost', port: int=5000):
        self.host = host
        self.port = port
        self.user_db = UserDB()

    def _app(self, environ, response) -> list:
        header = [
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Headers', 'Content-Type'),
            ('Access-Control-Allow-Methods', 'GET, POST'),
            ]
        
        request_method = environ.get('REQUEST_METHOD')

        if request_method == 'GET':
            query_string = environ.get('QUERY_STRING')
            if query_string:
                # クエリ文字列をパース
                qs = urllib.parse.parse_qs(query_string)

                # 自分のランキングを取得
                user = qs.get('user_name', [None])[0]
                # ランキング上位を取得
                limit = qs.get('limit', [None])[0]
                register = qs.get('register', [None])[0]
                if user and register:
                    res = self.user_db.is_registered(user)
                elif user and limit:
                    res = self.user_db.get_top_ranking(int(limit))
                elif user:
                    res = self.user_db.get_my_ranking(user)
                else:
                    res = self.user_db.get_top_ranking(10)

            # 辞書型をjsonに変換
            res = json.dumps(res).encode('utf-8')
            # ヘッダーセット
            header.append(('Content-Type', 'application/json; charset=utf-8'))
            header.append(('Content-Length', str(len(res))))
            # HTTPステータス
            status = '200 OK'

            # レスポンス送信
            response(status, header)
            return [res]
    
        if request_method == 'POST':
            wsgi_input = environ.get('wsgi.input')
            if wsgi_input is None:
                response('400 Bad Reuest', header)
                return []
            
            req = json.loads(wsgi_input.read(int(environ.get('CONTENT_LENGTH', 0))).decode('utf-8'))
            if req:
                user = req.get('user_name')
                score = req.get('score')
                if user and score:
                    self.user_db.set_my_money(user, score)
                    response('200 OK', header)
                    return [b'OK']
            response('400 Bad Request', header)
            return [b'Error']
        
    def start(self) -> None:
        with make_server(self.host, self.port, self._app) as hppd:
            print(f'server stating on {self.host}:{self.port}...')
            hppd.serve_forever()


def main() -> None:
    api_server = APIServer()
    api_server.start()

if __name__ == '__main__':
    main()

