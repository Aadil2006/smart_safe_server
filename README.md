# 🎬 Movie Review Sentiment Analyzer

## 📌 Project Overview
This project is an end-to-end Machine Learning web application designed to classify IMDB movie reviews into Positive, Negative, or NeutralMixed sentiments. It was developed as a Capstone Project for the Naviotech Internship.

## ⚙️ Features
 Custom Text Preprocessing Cleans raw HTML, special characters, and removes NLTK stopwords.
 TF-IDF Vectorization Extracts the top 5000 features for optimal model performance.
 Logistic Regression Model Trained on a perfectly balanced dataset of 50,000 IMDB reviews, achieving an accuracy of 88.92%.
 Smart Probability Threshold Detects mixedsarcastic reviews and categorizes them as Neutral if the model's confidence falls between 30% and 70%.
 Interactive UI Deployed locally using Streamlit.

## 🛠️ Tech Stack
 Language Python
 Libraries Pandas, Scikit-learn, NLTK, Regular Expressions (re), Pickle
 Frontend Streamlit

## 🚀 How to Run Locally
1. Clone this repository to your local machine.
2. Ensure you have Python installed.
3. Install the required dependencies
   ```bash
   pip install pandas scikit-learn nltk streamlit
