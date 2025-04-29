class LLMModelPricing:
    """ Pricing information model for LLM models. """

    def __init__(self, model, provider, input_tokens_price,
                 output_tokens_price, context, max_output_tokens, source, updated):
        self.model = model
        self.provider = provider
        self.input_tokens_price = input_tokens_price  # price per 1M tokens in USD
        self.output_tokens_price = output_tokens_price  # price per 1M tokens in USD
        self.context = context  # context window tokens (max input)
        self.max_output_tokens = max_output_tokens # max tokens the model can generate
        self.source = source  # source of the pricing information
        self.updated = updated

    def __str__(self):
        return f"Model: {self.model}, " \
               f"Provider: {self.provider}, " \
               f"Input Price: {self.input_tokens_price}, " \
               f"Output Price: {self.output_tokens_price}, " \
               f"Context: {self.context}, " \
               f"Max Output: {self.max_output_tokens}, " \
               f"Source: {self.source}, " \
               f"Updated: {self.updated}"
