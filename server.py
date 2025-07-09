import json
import datetime
import os
import sqlite3
import urllib.parse
from wsgiref.simple_server import make_server

class DB:
    DB_NAME = 'ranking.db'
    TABLE_NAME = 'ranking'
    KEY_LIST = ['log_time', 'user_name', 'score']

    # queryの一覧
    CREATE_TABLE           = f'CREATE TABLE {TABLE_NAME}(log_time TEXT, user_name TEXT PRIMARY KEY, score INTEGER)'                         # テーブル作成
    INSERT_NEW_SCORE       = f'INSERT INTO {TABLE_NAME}(log_time, user_name, score) VALUES (?, ?, ?)'                             # 新しいスコアを挿入
    UPDATE_SCORE           = f'UPDATE {TABLE_NAME} SET log_time = (?), score = (?) WHERE user_name = (?)'                                       # スコアを更新
    SEARCH_BY_USER           = f'SELECT * FROM {TABLE_NAME} WHERE user_name = (?)'                                                                # IDで検索
    COMPARE_SCORES_BY_USER   = f'SELECT * FROM {TABLE_NAME} WHERE score <= (?) AND user_name = (?)'                                               # IDでスコア比較
    TOP_RANKING            = f'SELECT * FROM {TABLE_NAME} ORDER BY score DESC LIMIT (?)'                                                 # トップランキング取得
    MY_RANKING             = f'SELECT * FROM(SELECT *, RANK() OVER(ORDER BY score DESC) AS ranking FROM {TABLE_NAME}) WHERE user_name = (?)'    # 自身のランキングを取得

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
    
    def write_new_score(self, user_name: str, score: int) -> None:
        # ログの時刻を取得
        log_time = self._get_log_time()
        # dbに登録されているか確認
        if self._execute(self.SEARCH_BY_USER, [user_name]):
            # 登録されているスコアより高ければ更新
            if self._execute(self.COMPARE_SCORES_BY_USER, [score, user_name]):
                # 更新
                self._execute(self.UPDATE_SCORE, [log_time, score, user_name])
        # dbに登録されていなければ追加
        else:
            self._execute(self.INSERT_NEW_SCORE, [log_time, user_name, score])

    def get_top_ranking(self, limit: int) -> dict:
        # ランキング取得
        ranking = self._execute(self.TOP_RANKING, [limit])
        # listをdictに変換
        # (log_time, user_name, score) -> {ranking: {log_time, user_name, score}}
        if ranking:
            sorted_ranking = {}
            for i, e in enumerate(ranking, 1):
                sorted_ranking[i] = dict(zip(self.KEY_LIST, e))
            return sorted_ranking
        return {}
    
    def get_my_ranking(self, id: str) -> dict:
        ranking = self._execute(self.MY_RANKING, [id])

        if ranking:
            return {str(ranking[0][-1]): dict(zip(self.KEY_LIST, ranking[0]))}
        
    def reset_ranking(self) -> None:
        try:
            os.remove(self.DB_NAME)
        except FileNotFoundError:
            pass

        self._execute(self.CREATE_TABLE)

class UserDB:
    DB_NAME    = 'users.db'
    TABLE_NAME = 'users'
    KEY_LIST   = ['log_time', 'id', 'user_name']

    # query一覧
    CREATE_TABLE        = f'CREATE TABLE {TABLE_NAME}(log_time TEXT, user_name TEXT PRIMARY KEY)'    # テーブル作成
    INSERT_USER         = f'INSERT INTO {TABLE_NAME}(log_time, user_name) VALUES (?, ?)'                     # 新しいスコアを挿入
    SEARCH_BY_USER_NAME = f'SELECT * FROM {TABLE_NAME} WHERE user_name = (?)'                                              # IDで検索

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
        res = self._execute(self.SEARCH_BY_USER_NAME, [user_name])
        if res:
            return f'Already used this name: {user_name}'
        else:
            log_time = self._get_log_time()
            self._execute(self.INSERT_USER, [log_time, user_name])
            return f'Registered the user: {user_name}'


class APIServer:
    def __init__(self, db: DB, host: str='localhost', port: int=5000):
        self.db   = db
        self.host = host
        self.port = port
        self.user_db   = UserDB()

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
                user = qs.get('user_name')
                if user:
                    res = self.db.get_my_ranking(user[0])

                # ランキング上位を取得
                limit = qs.get('limit')
                if limit:
                    res = self.db.get_top_ranking(int(limit[0]))

                # 登録済みか確認
                register = qs.get('register')
                if register:
                    res = self.user_db.is_registered(user[0])

            else:
                # 全ランキングを取得
                res = self.db.get_top_ranking(-1)

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
                if id and user and score:
                    self.db.write_new_score(user, score)
                    response('200 OK', header)
                    return []
            response('400 Bad Request', header)
            return []
        
    def start(self) -> None:
        with make_server(self.host, self.port, self._app) as hppd:
            print(f'server stating on {self.host}:{self.port}...')
            hppd.serve_forever()


def main() -> None:
    db = DB()
    db.reset_ranking()
    api_server = APIServer(db)
    api_server.start()

if __name__ == '__main__':
    main()

