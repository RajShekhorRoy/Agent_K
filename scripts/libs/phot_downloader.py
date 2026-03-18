import requests
path="01100"
url = "https://rest.kegg.jp/get/map{0}/image2x".format(path)
res = requests.get(url)
if res.status_code == 200:
    with open("../output/" + str(path) + ".png", "wb") as f:
        f.write(res.content)
    print("Saved!", len(res.content), "bytes")
else:
    print("Failed:", res.status_code)