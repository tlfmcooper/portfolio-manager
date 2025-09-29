import React, { useState, useEffect } from 'react';

const Tooltip = () => {
  const [tooltip, setTooltip] = useState({
    visible: false,
    content: '',
    x: 0,
    y: 0
  });

  useEffect(() => {
    const handleMouseEnter = (e) => {
      const tooltipContent = e.target.closest('[data-tooltip]')?.getAttribute('data-tooltip');
      if (tooltipContent) {
        setTooltip({
          visible: true,
          content: tooltipContent,
          x: e.clientX + 10,
          y: e.clientY - 10
        });
      }
    };

    const handleMouseMove = (e) => {
      if (tooltip.visible && e.target.closest('[data-tooltip]')) {
        setTooltip(prev => ({
          ...prev,
          x: e.clientX + 10,
          y: e.clientY - 10
        }));
      }
    };

    const handleMouseLeave = (e) => {
      if (!e.target.closest('[data-tooltip]')) {
        setTooltip(prev => ({ ...prev, visible: false }));
      }
    };

    // Add event listeners to the document
    document.addEventListener('mouseenter', handleMouseEnter, true);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave, true);

    return () => {
      document.removeEventListener('mouseenter', handleMouseEnter, true);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave, true);
    };
  }, [tooltip.visible]);

  if (!tooltip.visible) return null;

  return (
    <div
      className="tooltip"
      style={{
        position: 'fixed',
        left: tooltip.x,
        top: tooltip.y,
        zIndex: 9999,
        pointerEvents: 'none',
        backgroundColor: 'var(--color-charcoal-800)',
        color: 'var(--color-white)',
        padding: 'var(--space-12)',
        borderRadius: 'var(--radius-base)',
        fontSize: 'var(--font-size-sm)',
        maxWidth: '300px',
        boxShadow: 'var(--shadow-lg)',
        lineHeight: 'var(--line-height-normal)',
        opacity: 1,
        transform: 'translateY(0)',
        transition: 'opacity 0.2s ease, transform 0.2s ease'
      }}
    >
      {tooltip.content}
    </div>
  );
};

export default Tooltip;