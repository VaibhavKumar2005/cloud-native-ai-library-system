from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginAnonRateThrottle(AnonRateThrottle):
    scope = "login"


class QueryUserRateThrottle(UserRateThrottle):
    scope = "query"


class UploadUserRateThrottle(UserRateThrottle):
    scope = "upload"


class DocumentActionUserRateThrottle(UserRateThrottle):
    scope = "document_action"
