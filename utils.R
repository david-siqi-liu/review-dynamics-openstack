library(pROC)
library(car)

getREVar = function(model) {
  #' Computes the variance of the random effect
  #' 
  #' @param model. The model
  #' 
  #' @return the variance of the random effect
  
  df = data.frame(VarCorr(model))
  
  return(round(df$vcov, digits=2))
}

getLR = function(model0, model1) {
  #' Performs Log-Likelihood Ratio test on two models
  #' 
  #' @param model0. The unsaturaed/less-complex model
  #' @param model1. The saturated/more-complex model
  #' 
  #' @return The -2 * log-likelihood ratio, differences in degrees-of-freedom, and the p-value
  
  # get log-likelihoods
  L0 = logLik(model0)
  L1 = logLik(model1)
  # get -2 * log-likelihood ratio
  LR = -2 * (as.numeric(L0) - as.numeric(L1))
  # degrees-of-freedom difference
  df = attr(L1, "df") - attr(L0, "df")
  # get p-value from chi-square distribution
  pval = pchisq(LR, df, lower.tail=FALSE)
  
  return(data.frame('lr' = LR,
                    'diff_d.f.' = df,
                    'pval' = pval))
}

getAUC = function(model, data, target_var) {
  #' Computes AUC-ROC
  #' 
  #' @param model. The model
  #' @param data. The data
  #' @param target_var. The target variable
  #' 
  #' @return The AUC-ROC
  
  model_type = attr(model, "class")[1]
  labels = data[, target_var]
  # predict
  if(model_type == 'glmerMod'){
    preds = predict(model, newdata = data, type = 'response', allow.new.levels = TRUE)
  } else if (model_type == 'glm') {
    preds = predict(model, newdata = data, type = 'response')
  }
  # compute AUC-ROC
  auc = auc(labels, preds)
  
  return(auc)
}

getVariableSigAndSign = function(model) {
  #' Extracts Chisq value and computes the significance level and
  #' the sign of the coefficients for each variable
  #' 
  #' @param model. The model
  #' 
  #' @return the Chisq value, significance level and sign for each variable
  
  model_type = attr(model, "class")[1]
  # ANOVA
  if(model_type == 'glmerMod'){
    anova = data.frame(Anova(model, type = 3))
  } else {
    anova = data.frame(Anova(model, type = 3, test.statistic = 'Wald'))
  }
  chisq_col = 'Chisq'
  pval_col = 'Pr..Chisq.'
  # Significance
  anova$sig = "o"
  anova$sig[anova[, pval_col] < 0.05] = "*"
  anova$sig[anova[, pval_col] < 0.01] = "**"
  anova$sig[anova[, pval_col] < 0.001] = "***"
  # Coefficients
  if(model_type == 'glmerMod'){
    coefs = data.frame('val' = fixef(model))
  } else {
    coefs = data.frame('val' = coef(model))
  }
  # Sign
  coefs$sign = ifelse(coefs$val < 0, "(-)", "(+)")
  # Merge by row names/variables
  df = merge(anova, coefs, by = 0, all = TRUE)
  # Format
  df$variable = df$Row.names
  df[, chisq_col] = round(df[, chisq_col], digits=0)
  
  return(df[, c('variable', chisq_col, 'sig', 'sign')])
}
