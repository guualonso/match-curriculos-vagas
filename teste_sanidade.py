from src.matching.semantic_matcher import matcher_semantico

cv = "Cientista de dados com experiência em Python, Pandas, scikit-learn e aprendizado de máquina."
vaga_boa = "Vaga para cientista de dados com Python, aprendizado de máquina e scikit-learn."
vaga_ruim = "Desenvolvedor front-end com React, CSS e design de interfaces."

print("compatível  :", matcher_semantico.comparar_um(cv, vaga_boa).score_final)
print("incompatível:", matcher_semantico.comparar_um(cv, vaga_ruim).score_final)