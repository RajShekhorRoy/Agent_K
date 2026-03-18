from bs4 import BeautifulSoup
#works
def extract_most_similar_cluster(html_file):
    with open(html_file, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    similar_clusters = []

    # Locate the table containing the similarity results
    tables = soup.find_all("table", class_="region-table")
    for table in tables:
        rows_even = table.find_all("tr", class_="linked-row even")
        rows_odd =table.find_all("tr", class_="linked-row odd")
        rows = rows_even + rows_odd
        for row in rows:
            columns = row.find_all("td")
            if len(columns) >= 6:  # Ensure there are enough columns
                region = columns[0].get_text(strip=True)
                type = columns[1].get_text(strip=True)
                index_from = columns[2].get_text(strip=True)
                index_to = columns[3].get_text(strip=True)
                similarity = columns[4].get_text(strip=True) if columns[4] else "N/A"
                cluster_link = columns[5].find("a")
                cluster_name = cluster_link.get_text(strip=True) if cluster_link else "N/A"
                if cluster_link!=None:
                    cluster_link = cluster_link.attrs['href']

                similar_clusters.append((region,type,index_from,index_to, similarity, cluster_name,cluster_link))

    return similar_clusters

# Example usage:
html_file = '/home/rajroy/antismash_results_cb/consensus_cov/index.html'
most_similar_clusters = extract_most_similar_cluster(html_file)

for region,type,index_from, index_to,similarity, cluster_name,cluster_link in most_similar_clusters:
    print(f"Region: {region}, From: {index_from}, To: {index_to},Similarity: {similarity}, Most Similar Known Cluster: {cluster_name} Links{cluster_link}")
