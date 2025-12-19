import React from 'react';
import { useNavigate } from 'react-router-dom';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex flex-col items-center justify-center min-h-[80vh] text-center p-3">
        <h1 className="text-9xl font-bold mb-8 text-gray-800 dark:text-gray-100">
          404
        </h1>
        <h2 className="text-4xl mb-6 text-gray-700 dark:text-gray-200">
          Page Not Found
        </h2>
        <p className="mb-8 max-w-[600px] text-gray-600 dark:text-gray-300">
          The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.
        </p>
        <button
          onClick={() => navigate('/')}
          className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
        >
          Go to Homepage
        </button>
      </div>
    </div>
  );
};

export default NotFound;
