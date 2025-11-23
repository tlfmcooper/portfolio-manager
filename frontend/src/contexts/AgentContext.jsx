import React, { createContext, useContext, useState, useCallback } from 'react';

const AgentContext = createContext();

export const useAgentContext = () => {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgentContext must be used within an AgentProvider');
  }
  return context;
};

export const AgentProvider = ({ children }) => {
  // Global overrides (affects all components)
  const [globalParams, setGlobalParams] = useState({});
  
  // Component-specific overrides
  const [riskParams, setRiskParams] = useState({});
  const [frontierParams, setFrontierParams] = useState({});
  const [monteCarloParams, setMonteCarloParams] = useState({});
  const [cppiParams, setCPPIParams] = useState({});

  // Visual indicator that we are in a "Simulation Mode"
  const isAgentActive = Object.keys(globalParams).length > 0 || 
                        Object.keys(riskParams).length > 0 || 
                        Object.keys(frontierParams).length > 0 || 
                        Object.keys(monteCarloParams).length > 0 || 
                        Object.keys(cppiParams).length > 0;

  const updateGlobalParams = useCallback((params) => {
    setGlobalParams(prev => ({ ...prev, ...params }));
  }, []);

  const updateRiskParams = useCallback((params) => {
    setRiskParams(prev => ({ ...prev, ...params }));
  }, []);

  const updateFrontierParams = useCallback((params) => {
    setFrontierParams(prev => ({ ...prev, ...params }));
  }, []);

  const updateMonteCarloParams = useCallback((params) => {
    setMonteCarloParams(prev => ({ ...prev, ...params }));
  }, []);

  const updateCPPIParams = useCallback((params) => {
    setCPPIParams(prev => ({ ...prev, ...params }));
  }, []);

  // Crucial: Clears all agent overrides, instantly reverting charts to their default, real-time state.
  const resetAllParams = useCallback(() => {
    setGlobalParams({});
    setRiskParams({});
    setFrontierParams({});
    setMonteCarloParams({});
    setCPPIParams({});
  }, []);

  const value = {
    isAgentActive,
    globalParams,
    riskParams,
    frontierParams,
    monteCarloParams,
    cppiParams,
    updateGlobalParams,
    updateRiskParams,
    updateFrontierParams,
    updateMonteCarloParams,
    updateCPPIParams,
    resetAllParams
  };

  return (
    <AgentContext.Provider value={value}>
      {children}
    </AgentContext.Provider>
  );
};

export default AgentContext;
