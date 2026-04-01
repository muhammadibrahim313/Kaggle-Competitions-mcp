import pandas as pd
from sklearn.ensemble import RandomForestClassifier

train = pd.read_csv("data/train.csv")
test = pd.read_csv("data/test.csv")

features = ["Pclass", "Sex", "Age", "SibSp", "Parch", "Fare", "Embarked"]

train = train[["PassengerId", "Survived"] + features].copy()
test = test[["PassengerId"] + features].copy()

fill_values = {
    "Age": train["Age"].median(),
    "Fare": train["Fare"].median(),
    "Embarked": train["Embarked"].mode()[0]
}

X = pd.get_dummies(train[features].fillna(fill_values))
X_test = pd.get_dummies(test[features].fillna(fill_values)).reindex(columns=X.columns, fill_value=0)

model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X, train["Survived"])

predictions = model.predict(X_test)

submission = pd.DataFrame({
    "PassengerId": test["PassengerId"],
    "Survived": predictions
})

submission.to_csv("submission.csv", index=False)
print("submission.csv created")
