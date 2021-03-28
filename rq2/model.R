data = read.csv("data/rq2/rq2_all_norm.csv", header = TRUE)

load("rq2/outputs/formulas.Rdata")

# Null
print(null_form)
null_model = glm(formula = null_form, family = 'binomial', data = data)
save(null_model, file = "rq2/outputs/null_model.Rdata")

# Ex Patch
print(ex_patch_form)
ex_patch_model = glm(formula = ex_patch_form, family = 'binomial', data = data)
save(ex_patch_model, file = "rq2/outputs/ex_patch_model.Rdata")

# Ex Review
print(ex_review_form)
ex_review_model = glm(formula = ex_review_form, family = 'binomial', data = data)
save(ex_review_model, file = "rq2/outputs/ex_review_model.Rdata")

# Ex Social
print(ex_social_form)
ex_social_model = glm(formula = ex_social_form, family = 'binomial', data = data)
save(ex_social_model, file = "rq2/outputs/ex_social_model.Rdata")

# Full
print(full_form)
full_model = glm(formula = full_form, family = 'binomial', data = data)
save(full_model, file = "rq2/outputs/full_model.Rdata")

