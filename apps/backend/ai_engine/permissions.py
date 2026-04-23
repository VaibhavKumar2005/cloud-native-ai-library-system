"""
Custom permission classes for VeriRag API.
Implements fine-grained access control for different endpoints.
"""

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAdminUser(BasePermission):
    """
    Permission that checks if the user is a Django staff/admin user.
    
    Used to protect sensitive ops endpoints that should only be accessible
    to project administrators, not regular researchers/students.
    """
    
    message = "Only administrators can access this endpoint."
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated AND is a staff member (admin)
        """
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )


class IsAdminUserOrReadOnly(BasePermission):
    """
    Permission that allows any authenticated user to read,
    but only admins can create/update/delete.
    """
    
    def has_permission(self, request, view):
        # Read permissions are allowed to authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return bool(request.user and request.user.is_authenticated)
        
        # Write permissions are only allowed to admins
        return bool(request.user and request.user.is_staff)
