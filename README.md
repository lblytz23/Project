## Summary
>「車の達人」APPのQ&AのSummaryと推理。 
「車の達人」が提供する技術者とユーザーの多ラウンド対話・診断提案のレポートなど11万件Corpusを用いてモデルを構築します。
このモデルは対話テキスト、ユーザーの質問、車種などの情報を基づいて、Summary・推論を含むレポートテキストを出力できます。
>
>「車の達人」は、Online相談のカタチで車Ownerさんの質問を解決するAPPです。 Ownerさんは音声、テキストや写真で質問を投稿し、システムが自動的に該当な整備士にアサインして、タイムリーで効果的な相談サービスを提供しています。 プラットフォームの利用者が多いことと、似ている重複な質問が多いことから、以前はほとんどの質問がプラットフォーム上で回答されたことがあります。
何度も回答を繰り返したり、何度も問い合わせを繰り返すことは、整備士の時間がかかるだけでなく、ユーザーが解決策を得るまでの時間を長くしてしまい、双方のリソースを無駄にしてしまうことになります。
> 
> ユーザーが解答を得る時間を節約ために、機械学習を利用してプラットフォーム上に蓄積された大量の過去のQ&Aデータを用いて、モデルを訓練し、プラットフォームから取得する過去の多ラウンドQ&Aテキストに基づいて、完全な推薦レポートと回答を出力することで、ユーザーがAIの意図認識によってオンライン上でたん解答を得ることができるようにしたいと考えている。
> 

## Solution
### Step 1
> This program aims to train a AI to generate Q & A summary and Inference according to the article.
>
>Currently the first step, that is, building vocabulary table has been done.
>
>Based on the train data and test data, all words are given a index by using Jieba and Pandas
>
>Please run the program from Main_Entrance.py and the vocabulary table called "vocab.txt" will be generated in the output folder.
