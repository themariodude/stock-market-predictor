def persistence_baseline(prices):
    """
    Predict the next price using the current price.

    Example:
        input:  [100, 102, 101, 105]
        output: [100, 102, 101]

    The predictions correspond to the actual next values:
        actual: [102, 101, 105]
    """
    #Predicts the next stock price using the current stock price.
    #This provides a simple benchmark for evaluating ML model performance
    if len(prices) < 2:
        raise ValueError("At least two prices are required.")

    return prices[:-1]
