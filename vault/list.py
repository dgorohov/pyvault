from abc import ABC, abstractmethod


class ProfilesListing(ABC):

    @abstractmethod
    def list_profiles(self, fn):
        pass
