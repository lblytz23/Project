## Summary
>「車の達人」APPのQ&AのSummaryと推理。 
「車の達人」が提供する技術者とユーザーの多ラウンド対話・診断提案のレポートなど11万件Corpusを用いてモデルを構築します。
このモデルは対話テキスト、ユーザーの質問、車種などの情報を基づいて、Summary・推論を含むレポートテキストを出力できます。
>
>「車の達人」は、Online相談のカタチで車Ownerさんの質問を解決するAPPです。 Ownerさんは音声、テキストや写真で質問を投稿し、システムが自動的に該当な整備士にアサインして、タイムリーで効果的な相談サービスを提供しています。 プラットフォームの利用者が多いことと、似ている重複な質問が多いことから、以前はほとんどの質問がプラットフォーム上で回答されたことがあります。
何度も回答を繰り返したり、何度も問い合わせを繰り返すことは、整備士の時間がかかるだけでなく、ユーザーが解決策を得るまでの時間を長くしてしまい、双方のリソースを無駄にしてしまうことになります。
> 
> ユーザーが解答を得る時間を節約ために、機械学習を利用してプラットフォーム上に蓄積された大量の過去のQ&Aデータを用いて、モデルを訓練し、プラットフォームから取得する過去の多ラウンドQ&Aテキストに基づいて、完全な推薦レポートと回答を出力することで、ユーザーがAIの意図認識によってオンライン上で解答を得ることができるようにしたいと考えています。
> 

## Solution
### Step 1
> This program aims to train a AI to generate Q & A summary and Inference according to the article.
>
> Currently the first step, that is, building vocabulary table has been done.
>
> Based on the train data and test data, all words are given a index by using Jieba and Pandas
>
> Please run the program from Main Entrance and the vocabulary table called "vocab.txt" will be generated in the output folder.

### Step 2
> Create a file named Vocab_build.py for generating word embedding by using "Gensim".
> 
> After that, the dictionary matrix is created by using the dictionary built in the first step
> 
> In addition, I trained the word vectors with fasttext instead of word2vec.
>
> No other significant features were found, except for a relatively significant difference in the dimension of sentence length.

### Step 3
> The text data is trained by the Seq2Seq algorithm to complete the construction of the baseline model.
> 
> It contains encoder layer, decoder layer and attention layer. The size of vocabulary is limited to 30000 in order to boost training speed.

### Step 4
> Continue to make improvements to the baseline model by adding TEST mode, checkpoint, etc. The baseline has been completed.
> 
> The current TEST model uses a greedy search approach. In the next step, I will try to use the Beam Search approach. (in process).
> 
> Due to the capacity of local GPU, the vocabulary size is limited to 2000 in training section, which causes the model effect is not quite good.
> 
> I also tried to implement it on Google Cloud Platform, but ended up choosing the same parameter settings due to the instability of resource allocation during extended use.

### Step 5
> Further improvement of the structure of the program. The PGN model has been added and is structurally separated from the Seq2Seq model. The parameters "model" and "mode" can be used to control which model you want to use (Seq2Seq or PGN), and to test or train.
>
> Basically, the last update focuses on PGN. Beam Search and Coverage are also included to figure out the OOV and repeated issues. The current understanding of Beam Search is still shallow.
>
> The vocab_size is limited to 2000 due to the computer capacity limitation. If we can use the expanded vocabulary, we may get better performance.
>
>