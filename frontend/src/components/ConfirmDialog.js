import React from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    Button,
    Box
} from '@mui/material';
import { Warning } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

function ConfirmDialog({ 
    open, 
    onClose, 
    onConfirm, 
    title, 
    message, 
    confirmText, 
    cancelText,
    severity = "warning"
}) {
    const { t } = useTranslation('common');

    const getIcon = () => {
        switch (severity) {
            case "error":
                return <Warning sx={{ color: 'error.main', fontSize: 40, mb: 2 }} />;
            case "warning":
            default:
                return <Warning sx={{ color: 'warning.main', fontSize: 40, mb: 2 }} />;
        }
    };

    const getConfirmButtonColor = () => {
        switch (severity) {
            case "error":
                return "error";
            case "warning":
            default:
                return "warning";
        }
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="sm"
            fullWidth
            PaperProps={{
                sx: {
                    borderRadius: 2,
                    p: 1
                }
            }}
        >
            <DialogTitle sx={{ textAlign: 'center', pb: 1 }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    {getIcon()}
                    {title}
                </Box>
            </DialogTitle>
            
            <DialogContent>
                <DialogContentText sx={{ textAlign: 'center', fontSize: '1.1rem' }}>
                    {message}
                </DialogContentText>
            </DialogContent>
            
            <DialogActions sx={{ justifyContent: 'center', gap: 2, pb: 3 }}>
                <Button
                    onClick={onClose}
                    variant="outlined"
                    size="large"
                    sx={{ minWidth: 100 }}
                >
                    {cancelText || t('buttons.cancel')}
                </Button>
                <Button
                    onClick={onConfirm}
                    variant="contained"
                    color={getConfirmButtonColor()}
                    size="large"
                    sx={{ minWidth: 100 }}
                >
                    {confirmText || t('buttons.confirm')}
                </Button>
            </DialogActions>
        </Dialog>
    );
}

export default ConfirmDialog;