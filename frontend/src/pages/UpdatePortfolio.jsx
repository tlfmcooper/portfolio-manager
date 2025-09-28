
import React, { useState } from 'react';
import UpdatePortfolioModal from '../components/UpdatePortfolioModal';

const UpdatePortfolio = () => {
  const [isModalOpen, setIsModalOpen] = useState(true);

  const handleCloseModal = () => {
    setIsModalOpen(false);
    // You might want to navigate away or handle the state differently
  };

  return (
    <div>
      {/* This page can be used to host the modal or other related UI */}
      <UpdatePortfolioModal isOpen={isModalOpen} onClose={handleCloseModal} />
    </div>
  );
};

export default UpdatePortfolio;
