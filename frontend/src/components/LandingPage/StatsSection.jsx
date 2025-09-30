import React from 'react';

const StatsSection = () => {
  const stats = [
    { value: '10K+', label: 'Active Users', icon: '👥' },
    { value: '$2.5B+', label: 'Assets Managed', icon: '💰' },
    { value: '99.9%', label: 'Uptime', icon: '⚡' },
    { value: '150+', label: 'Countries', icon: '🌍' }
  ];

  return (
    <section className="py-16 lg:py-20 bg-gray-900/30 backdrop-blur-sm">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <div 
              key={index}
              className="text-center group cursor-pointer"
            >
              <div className="text-3xl mb-3 group-hover:scale-110 transition-transform duration-300">
                {stat.icon}
              </div>
              <div className="text-3xl lg:text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-2 group-hover:scale-105 transition-transform duration-300">
                {stat.value}
              </div>
              <div className="text-gray-400 text-sm lg:text-base font-medium">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default StatsSection;
