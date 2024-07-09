import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import re

'''

Experimenting with some ML techniques to shortlist startups

'''

file_path = '../data/flattened_data.csv'
df = pd.read_csv(file_path)

uk_companies = df[df['country'] == 'UK']
features = uk_companies[['description', 'tags', 'long_business_description']].fillna('')

uk_companies['combined_features'] = features.apply(lambda x: ' '.join(x), axis=1)

vectorizer = TfidfVectorizer(stop_words='english')
X = vectorizer.fit_transform(uk_companies['combined_features']).toarray()

scaler = StandardScaler()
X = scaler.fit_transform(X)

X_tensor = torch.tensor(X, dtype=torch.float32)

class Autoencoder(nn.Module):
    def __init__(self, input_dim, encoding_dim):
        super(Autoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, encoding_dim),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(encoding_dim, 512),
            nn.ReLU(),
            nn.Linear(512, input_dim),
            nn.Sigmoid()
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return encoded, decoded

input_dim = X_tensor.shape[1]
encoding_dim = 64
model = Autoencoder(input_dim, encoding_dim)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

num_epochs = 10
batch_size = 128

for epoch in range(num_epochs):
    permutation = torch.randperm(X_tensor.size()[0])
    for i in range(0, X_tensor.size()[0], batch_size):
        indices = permutation[i:i + batch_size]
        batch_x = X_tensor[indices]

        encoded, decoded = model(batch_x)
        loss = criterion(decoded, batch_x)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    print(f'Epoch {epoch+1}/{num_epochs}, Loss: {loss.item()}')

with torch.no_grad():
    encoded_features, _ = model(X_tensor)

encoded_features_np = encoded_features.numpy()

num_clusters = 15
kmeans = KMeans(n_clusters=num_clusters, random_state=42)
uk_companies['cluster'] = kmeans.fit_predict(encoded_features_np)

def find_best_cluster(profile_keywords):
    profile_vector = vectorizer.transform([profile_keywords]).toarray()
    profile_vector = scaler.transform(profile_vector)
    profile_tensor = torch.tensor(profile_vector, dtype=torch.float32)
    with torch.no_grad():
        encoded_profile, _ = model(profile_tensor)
    encoded_profile_np = encoded_profile.numpy()
    cluster = kmeans.predict(encoded_profile_np)[0]
    return cluster

def extract_resume_features(resume_text):
    skills = [
        'Deep Learning', 'Machine Learning', 'Distributed Systems', ' Microservices'
    ]
    found_skills = [skill for skill in skills if re.search(skill, resume_text, re.IGNORECASE)]
    
    experience_pattern = r'(Deep Learnign|AI|Software Engineer|Machine Learning Intern)'
    work_experience = re.findall(experience_pattern, resume_text)
    
    combined_features = ' '.join(found_skills + work_experience)
    
    return combined_features

with open('../resume.txt', 'r') as file:
    resume_text = file.read()

resume_keywords = extract_resume_features(resume_text)

best_cluster = find_best_cluster(resume_keywords)

top_10_companies = uk_companies[uk_companies['cluster'] == best_cluster].head(10)

top_10_companies.to_csv('top_10_uk_companies.csv', index=False)

print(top_10_companies[['title', 'link', 'description', 'category', 'business_name']])
