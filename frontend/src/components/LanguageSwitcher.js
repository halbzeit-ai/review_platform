import React from 'react';
import { 
    IconButton, 
    Menu, 
    MenuItem, 
    ListItemIcon, 
    ListItemText,
    Tooltip
} from '@mui/material';
import { Language as LanguageIcon } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { updateLanguagePreference } from '../services/api';

const languages = [
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
    { code: 'en', name: 'English', flag: '🇺🇸' }
];

function LanguageSwitcher() {
    const { i18n, t } = useTranslation('common');
    const [anchorEl, setAnchorEl] = React.useState(null);
    const open = Boolean(anchorEl);

    const handleClick = (event) => {
        setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const handleLanguageChange = async (languageCode) => {
        // Update frontend immediately
        i18n.changeLanguage(languageCode);
        handleClose();
        
        // Store in localStorage for persistence
        localStorage.setItem('language', languageCode);
        
        // Update user preference in backend if logged in
        const user = JSON.parse(localStorage.getItem('user'));
        if (user?.token) {
            try {
                await updateLanguagePreference(languageCode);
                console.log('Language preference updated successfully:', languageCode);
                
                // Update user object in localStorage
                const updatedUser = { ...user, preferred_language: languageCode };
                localStorage.setItem('user', JSON.stringify(updatedUser));
            } catch (error) {
                console.error('Failed to update language preference:', error);
                // Still allow language change in frontend even if backend fails
            }
        }
    };

    const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[0];

    return (
        <>
            <Tooltip title={t('language.switch')}>
                <IconButton
                    onClick={handleClick}
                    size="small"
                    sx={{ ml: 1 }}
                    aria-controls={open ? 'language-menu' : undefined}
                    aria-haspopup="true"
                    aria-expanded={open ? 'true' : undefined}
                >
                    <LanguageIcon />
                </IconButton>
            </Tooltip>
            
            <Menu
                id="language-menu"
                anchorEl={anchorEl}
                open={open}
                onClose={handleClose}
                onClick={handleClose}
                PaperProps={{
                    elevation: 0,
                    sx: {
                        overflow: 'visible',
                        filter: 'drop-shadow(0px 2px 8px rgba(0,0,0,0.32))',
                        mt: 1.5,
                        '& .MuiAvatar-root': {
                            width: 32,
                            height: 32,
                            ml: -0.5,
                            mr: 1,
                        },
                        '&:before': {
                            content: '""',
                            display: 'block',
                            position: 'absolute',
                            top: 0,
                            right: 14,
                            width: 10,
                            height: 10,
                            bgcolor: 'background.paper',
                            transform: 'translateY(-50%) rotate(45deg)',
                            zIndex: 0,
                        },
                    },
                }}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
                {languages.map((language) => (
                    <MenuItem
                        key={language.code}
                        onClick={() => handleLanguageChange(language.code)}
                        selected={language.code === i18n.language}
                    >
                        <ListItemIcon>
                            <span style={{ fontSize: '1.2em' }}>{language.flag}</span>
                        </ListItemIcon>
                        <ListItemText>
                            {language.name}
                        </ListItemText>
                    </MenuItem>
                ))}
            </Menu>
        </>
    );
}

export default LanguageSwitcher;