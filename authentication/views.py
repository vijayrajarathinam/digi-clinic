from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model
from .services import AuthenticationService, EmailVerificationService
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    ResendVerificationSerializer,
    EmailVerificationSerializer,
)

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user, error = AuthenticationService.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            role=serializer.validated_data.get("role", "patient"),
        )

        if user:
            EmailVerificationService.send_verification_email(user)

            auth_data, auth_error = AuthenticationService.authenticate_user(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )

            if auth_data:
                AuthenticationService.update_user_status(
                    auth_data["user"], is_online=True
                )
                return Response(
                    {
                        "message": "User registered successfully. Please check your email to verify your account",
                        "user": UserSerializer(auth_data["user"]).data,
                        "access_token": auth_data["access_token"],
                        "refresh_token": auth_data["refresh_token"],
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "error": f"registered successfully, but login failed with {auth_error}"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = UserLoginSerializer(data=request.data)

    if serializer.is_valid():
        auth_data, error = AuthenticationService.authenticate_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if auth_data:
            AuthenticationService.update_user_status(auth_data["user"], is_online=True)
            return Response(
                {
                    "message": "Login Successfully",
                    "user": UserSerializer(auth_data["user"]).data,
                    "access_token": auth_data["access_token"],
                    "refresh_token": auth_data["refresh_token"],
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": f"registered successfully, but login failed with {error}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

    return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    if refresh_token := request.data.get("refresh_token"):
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except (TokenError, InvalidToken) as ex:
            return Response(
                {"error": "Invalid refresh token", "message": str(ex)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

    AuthenticationService.update_user_status(request.user, is_online=False)
    return Response({"message": "logged out successfully"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def validate_token(request):
    try:
        AuthenticationService.update_user_status(request.user, is_online=True)
        return Response(
            {
                "valid": True,
                "user": UserSerializer(request.user).data,
                "message": "Token is valid",
            },
            status=status.HTTP_200_OK,
        )
    except Exception as ex:
        return Response(
            {
                "valid": False,
                "error": f"Token failed with {str(ex)}",
                "message": str(ex),
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = UserSerializer(request.user).data
    return Response({"user": user}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def token_refresh_custom(request):
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        user_id = refresh.payload.get("user_id")
        user = User.objects.get(id=user_id)

        AuthenticationService.update_user_status(user, is_online=True)
        return Response(
            {"access_token": access_token, "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )

    except (TokenError, InvalidToken, User.DoesNotExist) as ex:
        return Response(
            {"error": "Invalid refresh token", "message": str(ex)},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    serializer = EmailVerificationSerializer(data=request.data)

    if serializer.is_valid():
        token = serializer.validated_data["token"]

        user, error = EmailVerificationService.verify_email_token(token)

        if user:
            return Response(
                {
                    "message": "email verified successfully",
                    "user": UserSerializer(user).data,
                    "verified": True,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"verified": False, "error": error}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_verification_email(request):
    serializer = ResendVerificationSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            success, message = EmailVerificationService.resend_verification_email(user)

            if success:
                return Response(
                    {"message": message, "email_sent": True}, status=status.HTTP_200_OK
                )

            return Response(
                {"message": message, "email_sent": False},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "user with this email does not exist", "email_sent": False},
                status=status.HTTP_404_NOT_FOUND,
            )

    return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_verification_email_authenticated(request):
    if request.user.is_verified:
        return Response(
            {"error": "Email is already sent", "email_sent": False},
            status=status.HTTP_400_BAD_REQUEST,
        )

    success, message = EmailVerificationService.resend_verification_email(request.user)
    if success:
        return Response(
            {"message": message, "email_sent": True}, status=status.HTTP_200_OK
        )

    return Response(
        {"message": message, "email_sent": False}, status=status.HTTP_400_BAD_REQUEST
    )
