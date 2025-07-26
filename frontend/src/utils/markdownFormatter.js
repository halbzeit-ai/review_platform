import React from 'react';
import {
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Box
} from '@mui/material';

/**
 * Shared markdown formatting utility for converting LLM-generated markdown text to React components
 * Used across ProjectResults and DeckViewer components
 */
export const formatMarkdownText = (text) => {
  if (!text) return '';
  
  // Split into lines for better parsing
  const lines = text.split('\n');
  const elements = [];
  let currentKey = 0;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip empty lines
    if (!line) {
      continue;
    }
    
    // Handle headers (####, ###, ##, #)
    if (line.startsWith('####')) {
      elements.push(
        <Typography key={currentKey++} variant="subtitle1" sx={{ 
          mt: 1.5, mb: 0.8, fontWeight: 'bold', color: 'primary.dark', fontSize: '1rem' 
        }}>
          {line.replace(/^####\s*/, '')}
        </Typography>
      );
      continue;
    }
    
    if (line.startsWith('###')) {
      elements.push(
        <Typography key={currentKey++} variant="h6" sx={{ 
          mt: 2, mb: 1, fontWeight: 'bold', color: 'primary.main' 
        }}>
          {line.replace(/^###\s*/, '')}
        </Typography>
      );
      continue;
    }
    
    if (line.startsWith('##')) {
      elements.push(
        <Typography key={currentKey++} variant="h5" sx={{ 
          mt: 2.5, mb: 1.2, fontWeight: 'bold', color: 'primary.main' 
        }}>
          {line.replace(/^##\s*/, '')}
        </Typography>
      );
      continue;
    }
    
    if (line.startsWith('#') && !line.startsWith('##')) {
      elements.push(
        <Typography key={currentKey++} variant="h4" sx={{ 
          mt: 3, mb: 1.5, fontWeight: 'bold', color: 'primary.main' 
        }}>
          {line.replace(/^#\s*/, '')}
        </Typography>
      );
      continue;
    }
    
    // Handle numbered lists
    if (line.match(/^\d+\.\s/)) {
      const listItems = [];
      let j = i;
      
      // Collect consecutive numbered items
      while (j < lines.length && lines[j].trim().match(/^\d+\.\s/)) {
        listItems.push(lines[j].trim());
        j++;
      }
      
      elements.push(
        <List key={currentKey++} dense sx={{ my: 0.8, pl: 2 }}>
          {listItems.map((item, itemIndex) => (
            <ListItem key={itemIndex} sx={{ py: 0.2, pl: 0 }}>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <Chip 
                  label={item.match(/^(\d+)\./)[1]} 
                  size="small" 
                  color="primary" 
                  sx={{ width: 24, height: 24, fontSize: '0.75rem' }}
                />
              </ListItemIcon>
              <ListItemText 
                primary={
                  <Typography variant="body1" sx={{ fontSize: '0.9rem', lineHeight: 1.4 }}>
                    <span dangerouslySetInnerHTML={{ 
                      __html: item
                        .replace(/^\d+\.\s*/, '')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    }} />
                  </Typography>
                } 
              />
            </ListItem>
          ))}
        </List>
      );
      
      i = j - 1; // Skip processed lines
      continue;
    }
    
    // Handle bullet points and dashes (including indented ones)
    // Only match actual bullet points (* followed by space), not bold text (**bold**)
    if (line.match(/^[-*•]\s/) || /^\s+[-*•]\s/.test(lines[i])) {
      const listItems = [];
      let j = i;
      
      // Collect consecutive bullet items (including nested ones)
      while (j < lines.length && lines[j].trim() && 
             (lines[j].trim().match(/^[-*•]\s/) ||
              /^\s+[-*•]\s/.test(lines[j]) ||
              (j > i && lines[j].startsWith('  ') && !lines[j].trim().startsWith('#') && !lines[j].trim().match(/^\d+\.\s/)))) {
        if (lines[j].trim()) {
          listItems.push({
            content: lines[j],
            trimmed: lines[j].trim(),
            indentLevel: lines[j].length - lines[j].trimStart().length
          });
        }
        j++;
      }
      
      elements.push(
        <List key={currentKey++} dense sx={{ my: 0.8, pl: 1 }}>
          {listItems.map((itemObj, itemIndex) => {
            const item = itemObj.trimmed;
            const indentLevel = itemObj.indentLevel;
            
            // Determine nesting level based on indentation
            const nestLevel = Math.floor(indentLevel / 2); // 2 spaces = 1 nest level
            const isNested = nestLevel > 0;
            
            return (
              <ListItem key={itemIndex} sx={{ 
                py: 0.1, 
                pl: nestLevel * 2,  // Progressive indentation
                display: 'flex',
                alignItems: 'flex-start'
              }}>
                <ListItemIcon sx={{ minWidth: 20, mt: 0.6 }}>
                  <Box sx={{ 
                    width: isNested ? 3 : 4, 
                    height: isNested ? 3 : 4, 
                    borderRadius: '50%', 
                    bgcolor: isNested ? 'text.disabled' : 'text.secondary'
                  }} />
                </ListItemIcon>
                <ListItemText 
                  primary={
                    <Typography variant="body1" sx={{ fontSize: '0.9rem', lineHeight: 1.4 }}>
                      <span dangerouslySetInnerHTML={{ 
                        __html: item
                          .replace(/^[*\-•]\s*/, '')
                          .replace(/^\s+/, '')
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      }} />
                    </Typography>
                  } 
                />
              </ListItem>
            );
          })}
        </List>
      );
      
      i = j - 1; // Skip processed lines
      continue;
    }
    
    // Handle regular paragraphs and standalone bold text
    const paragraphLines = [];
    let j = i;
    
    // Collect consecutive non-header, non-list lines
    // Exclude lines that start with single * or - (bullet points) but include ** (bold text)
    while (j < lines.length && lines[j].trim() && 
           !lines[j].trim().startsWith('#') &&
           !lines[j].trim().match(/^\d+\.\s/) &&
           !lines[j].trim().match(/^[-*•]\s/) && // Only exclude single bullet markers, not **
           !/^\s+[-*•]\s/.test(lines[j])) {
      paragraphLines.push(lines[j].trim());
      j++;
    }
    
    if (paragraphLines.length > 0) {
      const paragraphText = paragraphLines.join(' ');
      
      // Check if this is a standalone bold line (like **Slide Overview**)
      const isStandaloneBold = paragraphLines.length === 1 && 
                               paragraphText.match(/^\*\*.*\*\*$/);
      
      elements.push(
        <Typography key={currentKey++} variant={isStandaloneBold ? "subtitle1" : "body1"} paragraph sx={{ 
          lineHeight: 1.6, 
          fontSize: isStandaloneBold ? '1rem' : '0.9rem',
          color: 'text.primary',
          mb: 1.2,
          textAlign: isStandaloneBold ? 'left' : 'justify',
          fontWeight: isStandaloneBold ? 'bold' : 'normal'
        }}>
          <span dangerouslySetInnerHTML={{ 
            __html: paragraphText
              .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
              .replace(/✓\s*/g, '')
              .replace(/✔\s*/g, '')
          }} />
        </Typography>
      );
      
      i = j - 1; // Skip processed lines
    }
  }
  
  return elements;
};