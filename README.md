# さと専用 X 投稿分析サイト

対象: `@sattoa_ball` のみ。初期データは2026-10-14の259件のJSON。

## 公開方法

1. GitHubで**新しいリポジトリ**を作る（既存のHoI4サイトには入れない）。
2. ZIPを展開し、`index.html`, `data.json`, `scripts/refresh.py`, `.github/workflows/hourly-refresh.yml` を**フォルダ構造を維持**してアップロードする。
3. Settings → Pages → Build and deployment → Deploy from a branch → `main` / `(root)` → Save。
4. 公開されたURLで検索、並べ替え、CSV保存を使用できる。

**重要:** GitHub Pagesは原則公開サイト。`data.json`の投稿情報も誰でも取得できる。GitHub Pagesはログイン認証を提供しない。自分だけで使う場合は公開せず `python -m http.server 8000` でローカル起動し `http://localhost:8000` を開くことを推奨。

## 自動更新と増加速度の履歴

- `.github/workflows/hourly-refresh.yml` を GitHub Actions が毎時17分（UTC）付近に実行する設定。
- 非公式の公開取得元（FxTwitter）から既知の投稿・直近の公開投稿を取得できた場合に `data.json` を更新します。リポジトリ変数 `SATO_ENABLE_UNOFFICIAL_REFRESH=0` を指定するとこの取得を停止できます。
- `scripts/record_history.py` が取得済み数値を日時付きで `metric-history.json` に追記し、`/growth/` で投稿ごとの前回比や1時間換算の増加速度を確認できます。
- 増加速度 = （新しい値 − 前の値）÷ 実際の経過時間（時間）。1時間ぴったりの測定やXのリアルタイム値を保証するものではありません。
- 元の取得元が停止した、インプレッションを返さない、GitHub Actionsが遅延・停止した場合、履歴も更新されません。
- 履歴作成以前の細かい推移は復元できません。初回には比較対象がないので、次の有効な取得が必要です。
- GitHub Pagesで公開している `metric-history.json` と `data.json` は誰でも閲覧できます。

## その他

- フィルタ：本文検索、投稿種別、期間
- ソート：日時、表示、いいね、保存、RP、返信、引用
- CSV：現在の検索結果をダウンロード
- 収録データ以外は表示できない。自動更新で取得できない指標は更新されない。
