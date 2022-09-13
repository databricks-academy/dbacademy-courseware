class AssetValidator:
    from .publisher_class import Publisher

    def __init__(self, publisher: Publisher):
        self.build_config = publisher.build_config
        self.publisher = publisher

    def validate_git_dbc(self, dbc_path):
        pass

    def validate_git_published_branch(self):
        pass

    def validate_git_published_versioned_branch(self):
        pass

    def validate_distribution_dbc(self):
        pass
