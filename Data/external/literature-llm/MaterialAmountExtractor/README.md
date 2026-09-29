# MaterialAmountExtractor
Extract mateirals' amounts from text.

Install
~~~~
If Git Large File Storage (lfs) is not installed on your computer, please install it fistly following the instruction on
	https://help.github.com/articles/installing-git-large-file-storage/.
	
Then
    git clone git@github.com:CederGroupHub/MaterialAmountExtractor.git
    cd MaterialAMountExtractor
    pip install -e .
~~~~
Use:

~~~~
input: sentence and materials in the sentence
output: materials with their amounts as dict
~~~~

Example:
~~~~
from MaterialAmountExtractor import get_materials_amounts
sentence = "In a typical synthesis of stacked SnS2 nanoplates, 0.35 g of tin tetrachloride pentahydrate (SnCl4·H2O) and 0.4 g of thiourea (Tu) were first dissolved into 25 mL of distilled water under mild stirring."
materials_in_sentence = ["tin tetrachloride pentahydrate","SnCl4·H2O","thiourea","Tu","water"]
m_m = get_materials_amounts.GetMaterialsAmounts(sentence, materials_in_sentence)
print(m_m.final_result())

## output:
## {'tin tetrachloride pentahydrate': ['0.35', 'g'], 'thiourea': ['0.4', 'g'], 'water': ['25', 'mL']}
