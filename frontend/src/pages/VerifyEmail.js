import React, { useState, useEffect } from 'react';
import { 
    Container, 
    Paper, 
    Typography, 
    Box, 
    CircularProgress, 
    Alert,
    Button,
    TextField
} from '@mui/material';
import { CheckCircle, Error, Email } from '@mui/icons-material';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../services/api';

function VerifyEmail() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { t } = useTranslation('auth');
    const [verificationStatus, setVerificationStatus] = useState('loading'); // loading, success, error
    const [message, setMessage] = useState('');
    const [resendEmail, setResendEmail] = useState('');
    const [resendLoading, setResendLoading] = useState(false);
    const [resendMessage, setResendMessage] = useState('');

    useEffect(() => {
        const token = searchParams.get('token');
        
        if (token) {
            verifyEmailToken(token);
        } else {
            setVerificationStatus('error');
            setMessage(t('verification.errors.noToken'));
        }
    }, [searchParams]);

    const verifyEmailToken = async (token) => {
        try {
            const response = await api.get(`/auth/verify-email?token=${token}`);
            setVerificationStatus('success');
            setMessage(response.data.message);
        } catch (error) {
            console.error('Verification error:', error);
            setVerificationStatus('error');
            setMessage(error.response?.data?.detail || t('verification.errors.invalidToken'));
        }
    };

    const handleResendVerification = async () => {
        if (!resendEmail) {
            setResendMessage(t('common:forms.required'));
            return;
        }

        setResendLoading(true);
        setResendMessage('');

        try {
            const response = await api.post('/auth/resend-verification', {
                email: resendEmail
            });
            setResendMessage(t('verification.resendSuccess'));
        } catch (error) {
            setResendMessage(error.response?.data?.detail || t('verification.errors.resendFailed'));
        }

        setResendLoading(false);
    };

    const renderContent = () => {
        switch (verificationStatus) {
            case 'loading':
                return (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                        <CircularProgress size={60} sx={{ mb: 2 }} />
                        <Typography variant="h6">{t('verification.verifying')}</Typography>
                    </Box>
                );

            case 'success':
                return (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                        <CheckCircle sx={{ fontSize: 60, color: 'success.main', mb: 2 }} />
                        <Typography variant="h5" gutterBottom>
                            {t('verification.success')}
                        </Typography>
                        <Typography variant="body1" sx={{ mb: 3 }}>
                            {t('verification.successMessage')}
                        </Typography>
                        <Button 
                            variant="contained" 
                            size="large"
                            onClick={() => navigate('/login')}
                        >
                            {t('verification.goToLogin')}
                        </Button>
                    </Box>
                );

            case 'error':
                return (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                        <Error sx={{ fontSize: 60, color: 'error.main', mb: 2 }} />
                        <Typography variant="h5" gutterBottom>
                            {t('verification.failed')}
                        </Typography>
                        <Typography variant="body1" sx={{ mb: 3 }}>
                            {message}
                        </Typography>
                        
                        {/* Resend verification section */}
                        <Paper sx={{ p: 3, mt: 3, backgroundColor: 'grey.50' }}>
                            <Typography variant="h6" gutterBottom>
                                {t('verification.resendTitle')}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mt: 2 }}>
                                <TextField
                                    label={t('common:forms.email')}
                                    variant="outlined"
                                    value={resendEmail}
                                    onChange={(e) => setResendEmail(e.target.value)}
                                    sx={{ flexGrow: 1 }}
                                    disabled={resendLoading}
                                />
                                <Button
                                    variant="contained"
                                    onClick={handleResendVerification}
                                    disabled={resendLoading}
                                    startIcon={resendLoading ? <CircularProgress size={20} /> : <Email />}
                                >
                                    {resendLoading ? t('verification.resendLoading') : t('verification.resendButton')}
                                </Button>
                            </Box>
                            {resendMessage && (
                                <Alert severity="info" sx={{ mt: 2 }}>
                                    {resendMessage}
                                </Alert>
                            )}
                        </Paper>

                        <Box sx={{ mt: 3 }}>
                            <Button 
                                variant="outlined" 
                                onClick={() => navigate('/login')}
                            >
                                {t('verification.backToLogin')}
                            </Button>
                        </Box>
                    </Box>
                );

            default:
                return null;
        }
    };

    return (
        <Container maxWidth="sm" sx={{ mt: 8 }}>
            <Paper elevation={3} sx={{ p: 4 }}>
                <Box sx={{ textAlign: 'center', mb: 3 }}>
                    <Typography variant="h4" component="h1" gutterBottom>
                        {t('verification.title')}
                    </Typography>
                    <Typography variant="subtitle1" color="text.secondary">
                        {t('verification.subtitle')}
                    </Typography>
                </Box>
                
                {renderContent()}
            </Paper>
        </Container>
    );
}

export default VerifyEmail;