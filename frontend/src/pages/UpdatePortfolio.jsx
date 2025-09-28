
import React, { useState } from 'react';
import UpdatePortfolioModal from '../components/UpdatePortfolioModal';

const UpdatePortfolio = () => {
  const [isModalOpen, setIsModalOpen] = useState(true);

  const handleCloseModal = () => {
    setIsModalOpen(false);
    // You might want to navigate away or handle the state differently
  };

  return (
    <section className="dashboard-section active">
      <h2 style={{ 
        marginBottom: 'var(--space-24)', 
        fontSize: 'var(--font-size-2xl)', 
        color: 'var(--color-text)',
        fontWeight: 'var(--font-weight-semibold)'
      }}>
        Update Portfolio
      </h2>
      <div className="explanation-card" style={{
        backgroundColor: 'var(--color-bg-2)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-20)',
        marginBottom: 'var(--space-24)'
      }}>
        <p style={{ 
          margin: 0, 
          fontSize: 'var(--font-size-base)', 
          color: 'var(--color-text)', 
          lineHeight: 'var(--line-height-normal)' 
        }}>
          Manage your portfolio holdings by buying new assets, selling existing positions, or editing quantities and costs. 
          All transactions will be properly recorded and your portfolio metrics will be updated automatically.
        </p>
      </div>
      {/* This page can be used to host the modal or other related UI */}
      <UpdatePortfolioModal isOpen={isModalOpen} onClose={handleCloseModal} />
    </section>
  );
};

export default UpdatePortfolio;
