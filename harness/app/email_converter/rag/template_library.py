class TemplateLibrary:
    
    def select(
        self,
        slots: dict,
    ) -> str:

        images = slots.get(
            "images",
            [],
        )

        tables = slots.get(
            "tables",
            [],
        )

        # Product / catalogue style

        if (
            len(images) >= 2
            and tables
        ):

            return "product"

        # Campaign / visual email

        if images:

            return "hero"

        # Text/document-driven email

        return "text_first"