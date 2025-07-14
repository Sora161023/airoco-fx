import json
import datetime
import os
import sqlite3
import urllib.parse
from wsgiref.simple_server import make_server

class UserDB:
    DB_NAME    = 'users.db'
    TABLE_NAME = 'users'
    KEY_LIST   = ['log_time', 'user_name', 'money', 'stocks_json']

    # query一覧
    CREATE_TABLE = f'''
        CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
            log_time TEXT,
            user_name TEXT PRIMARY KEY,
            money INTEGER, 
            stocks_json TEXT
        )
    '''
    INSERT_USER = f'''
        INSERT INTO {TABLE_NAME}(log_time, user_name, money, stocks_json)
        VALUES (?, ?, ?, ?)
    '''
    UPDATE_USER = f'''
        UPDATE {TABLE_NAME} SET log_time = ?, money = ?, stocks_json = ? WHERE user_name = ?
    '''
    SELECT_USER = f'''
        SELECT * FROM {TABLE_NAME} WHERE user_name = ?
    '''
    SELECT_TOP = f'''
        SELECT * FROM {TABLE_NAME} ORDER BY money DESC LIMIT ?
    '''
    SELECT_RANKING = f'''
        SELECT *, RANK() OVER(ORDER BY money DESC) as ranking FROM {TABLE_NAME} WHERE user_name = ?
    '''                                # IDで検索

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
            initial_stocks = {
                "co2": {"stock": 0, "special_stocks": 0},
                "temp": {"stock": 0, "special_stocks": 0},
                "humid": {"stock": 0, "special_stocks": 0}
            }
            stocks_json = json.dumps(initial_stocks)
            self._execute(self.INSERT_USER, [log_time, user_name, 10000, stocks_json])
            return {"success": True, "message": f"Registered the user: {user_name}"}

    def set_user_data(self, user_name, money, stocks):
        log_time = self._get_log_time()
        stocks_json = json.dumps(stocks)
        if self._execute(self.SELECT_USER, [user_name]):
            self._execute(self.UPDATE_USER, [log_time, money, stocks_json, user_name])
        else:
            self._execute(self.INSERT_USER, [log_time, user_name, money, stocks_json])

    def get_user_data(self, user_name):
        res = self._execute(self.SELECT_USER, [user_name])
        if res:
            return {1: dict(zip(self.KEY_LIST, res[0]))}
        return {}

    def get_top_ranking(self, limit):
        query = f'''
            SELECT log_time, user_name, money, stocks_json,
                RANK() OVER(ORDER BY money DESC) as ranking
            FROM {self.TABLE_NAME}
            LIMIT ?
        '''
        res = self._execute(query, [limit])
        if res:
            return {
                str(row[-1]): dict(zip(self.KEY_LIST, row[:-1]))
                for row in res
            }
        return {}

    def get_my_ranking(self, user_name):
        query = f'''
            SELECT log_time, user_name, money, stocks_json,
                RANK() OVER(ORDER BY money DESC) as ranking
            FROM {self.TABLE_NAME}
            WHERE user_name = ?
        '''
        res = self._execute(query, [user_name])
        if res:
            return {
                str(res[0][-1]): dict(zip(self.KEY_LIST, res[0][:-1]))
            }
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
                get_money_flag = qs.get('get_money', [None])[0]
                get_stocks_flag = qs.get('get_stocks', [None])[0]

                if user and register:
                    res = self.user_db.is_registered(user)
                elif user and get_money_flag:
                    user_data = self.user_db.get_user_data(user)
                    if user_data:
                        res = {"money": user_data[1]["money"]}
                    else:
                        res = {"money": 10000}

                elif user and get_stocks_flag:
                    user_data = self.user_db.get_user_data(user)
                    if user_data:
                        res = json.loads(user_data[1]["stocks_json"])
                    else:
                        res = {
                            "co2": {"stock": 0, "special_stocks": 0},
                            "temp": {"stock": 0, "special_stocks": 0},
                            "humid": {"stock": 0, "special_stocks": 0}
                        }

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
            length = int(environ.get('CONTENT_LENGTH', 0))
            req = json.loads(environ['wsgi.input'].read(length).decode('utf-8'))
            user = req.get('user_name')
            money = req.get('money')
            stocks = req.get('stocks')
            if user and money is not None and stocks is not None:
                self.user_db.set_user_data(user, money, stocks)
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

