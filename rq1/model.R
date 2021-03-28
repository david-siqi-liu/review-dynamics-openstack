library(lme4)

data = read.csv("rq1/data/rq1/rq1_all_norm.csv", header = TRUE)

load("rq1/outputs/formulas.Rdata")

# Null
null_model = glmer(null_form,
                   family = 'binomial',
                   data = data,
                   control = glmerControl(optimizer = 'bobyqa', optCtrl = list(maxfun=1e6)))

save(null_model, file = "outputs/null_model.Rdata")

# Exclude patch
ex_patch_model = glmer(ex_patch_form,
                       family = 'binomial',
                       data = data,
                       control = glmerControl(optimizer = 'bobyqa', optCtrl = list(maxfun=1e6)))

save(ex_patch_model, file = "outputs/ex_patch_model.Rdata")

# Exclude dynamic
ex_dynamic_model = glmer(ex_dynamic_form,
                         family = 'binomial',
                         data = data,
                         control = glmerControl(optimizer = 'bobyqa', optCtrl = list(maxfun=1e6)))

save(ex_dynamic_model, file = "outputs/ex_dynamic_model.Rdata")

# Exclude reviewer
ex_reviewer_model = glmer(ex_reviewer_form,
                          family = 'binomial',
                          data = data,
                          control = glmerControl(optimizer = 'bobyqa', optCtrl = list(maxfun=1e6)))

save(ex_reviewer_model, file = "outputs/ex_reviewer_model.Rdata")

# Full
full_model = glmer(full_form,
                   family = 'binomial',
                   data = data,
                   control = glmerControl(optimizer = 'bobyqa', optCtrl = list(maxfun=1e6)))

save(full_model, file = "outputs/full_model.Rdata")