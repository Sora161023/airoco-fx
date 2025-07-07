import json
import datetime
import os
import sqlite3
import urllib.parse
from wsgiref.simple_server import make_server

class DB:
    DB_NAME = 'ranking.db'
    TABLE_NAME = 'ranking'
    KEY_LIST = ['log_time', 'id', 'user_name', 'score']

    # queryの一覧
    CREATE_TABLE           = f'CREATE TABLE {TABLE_NAME}(log_time TEXT, id TEXT, user_name TEXT, score INTEGER)'                         # テーブル作成
    INSERT_NEW_SCORE       = f'INSERT INTO {TABLE_NAME}(log_time, id, user_name, score) VALUES (?, ?, ?, ?)'                             # 新しいスコアを挿入
    UPDATE_SCORE           = f'UPDATE {TABLE_NAME} SET log_time = (?), score = (?) WHERE id = (?)'                                       # スコアを更新
    SEARCH_BY_ID           = f'SELECT * FROM {TABLE_NAME} WHERE id = (?)'                                                                # IDで検索
    COMPARE_SCORES_BY_ID   = f'SELECT * FROM {TABLE_NAME} WHERE score <= (?) AND id = (?)'                                               # IDでスコア比較
    TOP_RANKING            = f'SELECT * FROM {TABLE_NAME} ORDER BY score DESC LIMIT (?)'                                                 # トップランキング取得
    MY_RANKING             = f'SELECT * FROM(SELECT *, RANK() OVER(ORDER BY score DESC) AS ranking FROM {TABLE_NAME}) WHERE id = (?)'    # 自身のランキングを取得

    def _execute(self, query, params=()) -> list:
        """queryを実行"""
        with sqlite3.connect(self.DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            res = cur.fetchall

            return res
    
    def _get_log_time(self) -> str:
        """現在時刻をYYYY-MM-DD HH:MM:SSで表示"""
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def write_new_score(self, id: str, user_name: str, score: int) -> None:
        # ログの時刻を取得
        log_time = self._get_log_time()
        # dbに登録されているか確認
        if self._execute(self.SEARCH_BY_ID, [id]):
            # 登録されているスコアより高ければ更新
            if self._execute(self.COMPARE_SCORES_BY_ID, [score, id]):
                # 更新
                self._execute(self.UPDATE_SCORE, [log_time, score, id])
        # dbに登録されていなければ追加
        else:
            self._execute(self.INSERT_NEW_SCORE, [log_time, id, user_name, score])

    def get_top_ranking(self, limit: int) -> dict:
        # ランキング取得
        ranking = self._execute(self.TOP_RANKING, [limit])
        # listをdictに変換
        # (log_time, uuid, user_name, score) -> {ranking: {log_time, uuid, user_name, score}}
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
    
db = DB()
print(db._get_log_time())

