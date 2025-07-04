// Copy to clipboard functionality for code blocks
document.addEventListener('DOMContentLoaded', function() {
    // Add copy buttons to all code blocks
    const codeBlocks = document.querySelectorAll('.highlight pre');
    
    codeBlocks.forEach(function(codeBlock) {
        // Create copy button
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-btn';
        copyButton.textContent = 'Copy';
        copyButton.setAttribute('title', 'Copy to clipboard');
        
        // Add click handler
        copyButton.addEventListener('click', function() {
            const code = codeBlock.textContent;
            
            if (navigator.clipboard) {
                // Modern approach
                navigator.clipboard.writeText(code).then(function() {
                    copyButton.textContent = 'Copied!';
                    copyButton.style.background = '#27ae60';
                    setTimeout(function() {
                        copyButton.textContent = 'Copy';
                        copyButton.style.background = '';
                    }, 2000);
                });
            } else {
                // Fallback approach
                const textArea = document.createElement('textarea');
                textArea.value = code;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    copyButton.textContent = 'Copied!';
                    copyButton.style.background = '#27ae60';
                    setTimeout(function() {
                        copyButton.textContent = 'Copy';
                        copyButton.style.background = '';
                    }, 2000);
                } catch (err) {
                    copyButton.textContent = 'Failed';
                    setTimeout(function() {
                        copyButton.textContent = 'Copy';
                    }, 2000);
                }
                document.body.removeChild(textArea);
            }
        });
        
        // Add button to code block container
        const container = codeBlock.parentElement;
        container.style.position = 'relative';
        container.appendChild(copyButton);
    });
});