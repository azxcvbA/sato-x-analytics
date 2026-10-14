# さと専用 X 投稿分析サイト

対象: `@sattoa_ball` のみ。初期データは2026-10-14の259件のJSON。

## 公開方法

1. GitHubで**新しいリポジトリ**を作る（既存のHoI4サイトには入れない）。
2. ZIPを展開し、`index.html`, `data.json`, `scripts/refresh.py`, `.github/workflows/hourly-refresh.yml` を**フォルダ構造を維持**してアップロードする。
3. Settings → Pages → Build and deployment → Deploy from a branch → `main` / `(root)` → Save。
4. 公開されたURLで検索、並べ替え、CSV保存を使用できる。

**重要:** GitHub Pagesは原則公開サイト。`data.json`の投稿情報も誰でも取得できる。GitHub Pagesはログイン認証を提供しない。自分だけで使う場合は公開せず `python -m http.server 8000` でローカル起動し `http://localhost:8000` を開くことを推奨。

## 自動更新の現状

GitHub Actionsは毎時17分(UTC)に起動する設定。ただし **初期状態ではXから自動取得しない**。X公式APIには継続無料の読み取りを保証する方法がないため、費用ゼロを守るための設計。

実験的に、**既に収録されている直近20投稿の公開エンゲージメント数**を、非公式の第三者APIから毎時取得する機能を同梱。実行するにはGitHubのSettings → Secrets and variables → Actions → Variables → New repository variableで `SATO_ENABLE_UNOFFICIAL_REFRESH` = `1` を設定する。

このAPIは非公式で、成功・継続利用・各指標の取得を保証しない。特にブックマーク数が欠けることがある。取得できない項目は以前の値を維持し、失敗時はファイルを変更しない。**新規投稿の自動発見は未実装**。GitHub Actions自体が正常終了してもデータ更新が成功したとは限らない。第三者サービスへのアクセスに関する利用条件は有効化前に確認すること。

新しい投稿は、JSONを再エクスポートして `data.json` と差し替えるか、サイトの「JSONをローカル読込」で表示できる。ローカル読込はサーバーへアップロードされない。

## その他

- フィルタ：本文検索、投稿種別、期間
- ソート：日時、表示、いいね、保存、RP、返信、引用
- CSV：現在の検索結果をダウンロード
- 収録データ以外は表示できない。自動更新で取得できない指標は更新されない。
