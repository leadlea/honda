import React from 'react';
import { useAuth } from '../../contexts/AuthContext';

interface RoleBasedComponentProps {
  children: React.ReactNode;
  allowedRoles: ReadonlyArray<'veteran' | 'admin' | 'external_recruiter'>;
  fallback?: React.ReactNode;
}

const RoleBasedComponent: React.FC<RoleBasedComponentProps> = ({
  children,
  allowedRoles,
  fallback = null,
}) => {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || !user) {
    return <>{fallback}</>;
  }

  if (!allowedRoles.includes(user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

export default RoleBasedComponent;