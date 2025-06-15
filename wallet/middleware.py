import logging
import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.http import JsonResponse
from django.core.exceptions import SuspiciousOperation


logger = logging.getLogger('wallet')
auth_logger = logging.getLogger('wallet.auth')
security_logger = logging.getLogger('wallet.security')


class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Мидлвеар для логирования запросов безопасности и производительности
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        Логирование входящих запросов
        """
        request.start_time = time.time()
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        request.client_ip = ip
        
        if request.path.startswith('/api/'):
            user_info = f"user={request.user.username}" if request.user.is_authenticated else "user=anonymous"
            logger.debug(
                f"API_REQUEST | {request.method} {request.path} | {user_info} | ip={ip}"
            )
            
            if request.method == 'POST' and '/deposit/' in request.path:
                security_logger.info(f"DEPOSIT_ATTEMPT | {user_info} | ip={ip}")
            elif request.method == 'POST' and '/transfer/' in request.path:
                security_logger.info(f"TRANSFER_ATTEMPT | {user_info} | ip={ip}")

    def process_response(self, request, response):
        """
        Логирование ответов и производительности
        """
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            if request.path.startswith('/api/'):
                user_info = f"user={request.user.username}" if request.user.is_authenticated else "user=anonymous"
                
                if duration > 1.0:
                    security_logger.warning(
                        f"SLOW_REQUEST | {request.method} {request.path} | {user_info} | "
                        f"duration={duration:.3f}s | status={response.status_code}"
                    )
                
                if response.status_code >= 400:
                    log_level = security_logger.error if response.status_code >= 500 else security_logger.warning
                    log_level(
                        f"ERROR_RESPONSE | {request.method} {request.path} | {user_info} | "
                        f"status={response.status_code} | duration={duration:.3f}s | ip={getattr(request, 'client_ip', 'unknown')}"
                    )
                else:
                    logger.debug(
                        f"API_RESPONSE | {request.method} {request.path} | {user_info} | "
                        f"status={response.status_code} | duration={duration:.3f}s"
                    )
        
        return response

    def process_exception(self, request, exception):
        """
        Логирование исключений
        """
        user_info = f"user={request.user.username}" if request.user.is_authenticated else "user=anonymous"
        ip = getattr(request, 'client_ip', 'unknown')
        
        if isinstance(exception, SuspiciousOperation):
            security_logger.error(
                f"SUSPICIOUS_OPERATION | {request.method} {request.path} | {user_info} | "
                f"ip={ip} | exception={str(exception)}"
            )
        else:
            logger.error(
                f"UNHANDLED_EXCEPTION | {request.method} {request.path} | {user_info} | "
                f"ip={ip} | exception={type(exception).__name__}: {str(exception)}"
            )
        
        return None


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Логирование успешного входа пользователя
    """
    ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    
    auth_logger.info(
        f"USER_LOGIN_SUCCESS | user={user.username} | ip={ip} | user_agent={user_agent}"
    )
    security_logger.info(
        f"LOGIN_SUCCESS | user={user.username} | ip={ip}"
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Логирование выхода пользователя
    """
    if user:
        ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', 'unknown'))
        
        auth_logger.info(
            f"USER_LOGOUT | user={user.username} | ip={ip}"
        )
        security_logger.info(
            f"LOGOUT | user={user.username} | ip={ip}"
        )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    Логирование неудачной попытки входа
    """
    ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
    username = credentials.get('username', 'unknown')
    
    auth_logger.warning(
        f"USER_LOGIN_FAILED | username={username} | ip={ip} | user_agent={user_agent}"
    )
    security_logger.warning(
        f"LOGIN_FAILED | username={username} | ip={ip}"
    )


class RateLimitingMiddleware(MiddlewareMixin):
    """
    Простой мидлвеар для мониторинга частоты запросов
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Мониторинг частоты запросов от одного IP
        """
        if request.path.startswith('/api/'):
            ip = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR'))
            current_time = time.time()
            
            cutoff_time = current_time - 60
            self.request_counts = {
                ip_addr: times for ip_addr, times in self.request_counts.items()
                if any(t > cutoff_time for t in times)
            }
            
            if ip not in self.request_counts:
                self.request_counts[ip] = []
            
            self.request_counts[ip] = [
                t for t in self.request_counts[ip] if t > cutoff_time
            ]
            
            self.request_counts[ip].append(current_time)
            
            if len(self.request_counts[ip]) > 100:
                user_info = f"user={request.user.username}" if request.user.is_authenticated else "user=anonymous"
                security_logger.warning(
                    f"RATE_LIMIT_EXCEEDED | ip={ip} | {user_info} | "
                    f"requests_count={len(self.request_counts[ip])}"
                )
        
        return None 