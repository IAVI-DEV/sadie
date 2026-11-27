import json

from sadie.germlines import GermlineManager
from sadie.germlines.g3_adapter import GermlineToG3Adapter

manager = GermlineManager()
adapter = GermlineToG3Adapter()

genes = manager.get_genes("human", "V", "H")[:5]
response_json = [adapter.to_g3_format(g) for g in genes]

print(json.dumps(response_json, indent=4))
json.dump(response_json, open("human_v.json", "w"), indent=4)
