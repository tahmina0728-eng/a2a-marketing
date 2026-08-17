class BrandRAG:
    
    """
    Connect this to your existing
    Cloud SQL / pgvector brand knowledge.

    Keep the return contract stable.
    """

    def search(
        self,
        brand_name: str,
    ) -> dict:

        return {

            "brand_name":
                brand_name,

            "brand_colors":
                [],

            "tone_of_voice":
                "professional and clear",

            "do_say":
                [],

            "dont_say":
                [],
        }