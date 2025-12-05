'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Plane, Snowflake, Flower, Sun, Leaf, CheckCircle2, AlertCircle, Loader2, MapPin, Calendar, DollarSign, Users, Sparkles, ArrowRight } from 'lucide-react';
import { streamChat, resumeChat, StreamEvent } from '@/lib/api';
import React from 'react';

interface Message {
  id: string;
  type: 'user' | 'system' | 'step' | 'research' | 'analysis' | 'season' | 'planning' | 'question' | 'result' | 'error' | 'interrupt';
  step?: string;
  content: string;
  data?: any;
  timestamp: Date;
}

interface InterruptData {
  type: 'question' | 'destination_selection';
  question: string;
  field?: string;
  options?: any[];
  missing_info?: string[];
  budget_allocation?: any;
}

const SEASON_ICONS = {
  winter: Snowflake,
  spring: Flower,
  summer: Sun,
  fall: Leaf
};

const SEASON_COLORS = {
  winter: 'text-blue-500',
  spring: 'text-pink-500',
  summer: 'text-yellow-500',
  fall: 'text-orange-500'
};

const SEASON_GRADIENTS = {
  winter: 'from-blue-100 to-cyan-100',
  spring: 'from-pink-100 to-rose-100',
  summer: 'from-yellow-100 to-orange-100',
  fall: 'from-orange-100 to-amber-100'
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'system',
      content: '✈️ Welcome to AI Travel Planner!\n\nLet\'s plan your perfect trip! I just need a few details to get started.\n\nYou can say:\n• "I want to travel for 7 days in summer with a $3000 budget"\n• "Plan a 5-day spring trip to Paris for 2 people"\n• Or just tell me your budget, duration, and preferred season!',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [interruptData, setInterruptData] = useState<InterruptData | null>(null);
  const [userResponse, setUserResponse] = useState('');
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (message: Omit<Message, 'id' | 'timestamp'>) => {
    setMessages((prev) => [
      ...prev,
      {
        ...message,
        id: Date.now().toString() + Math.random(),
        timestamp: new Date(),
      },
    ]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);
    setCurrentStep(0);
    setInterruptData(null);
    setSelectedSeason(null);

    addMessage({ type: 'user', content: userMessage });

    try {
      for await (const event of streamChat(userMessage, conversationId || undefined)) {
        handleStreamEvent(event);
      }
    } catch (error) {
      console.error('Error:', error);
      addMessage({ type: 'error', content: 'Sorry, I encountered an error. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleInterruptResponse = async (value: any) => {
    if (!conversationId || !interruptData) return;

    setIsLoading(true);
    const currentInterrupt = interruptData;
    setInterruptData(null);
    setUserResponse('');

    // Add user's response to chat
    let responseText = '';
    if (currentInterrupt.type === 'destination_selection') {
      const selectedOption = currentInterrupt.options?.[value];
      responseText = selectedOption?.name || `Option ${value}`;
    } else {
      responseText = String(value);
    }
    
    addMessage({ type: 'user', content: responseText });

    try {
      for await (const event of resumeChat(conversationId, value)) {
        handleStreamEvent(event);
      }
    } catch (error) {
      console.error('Error:', error);
      addMessage({ type: 'error', content: 'Sorry, I encountered an error. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStreamEvent = (event: StreamEvent) => {
    console.log('📥 Received event:', event.type, event);
    
    if (event.conversation_id && !conversationId) {
      setConversationId(event.conversation_id);
    }

    switch (event.type) {
      case 'system':
        if (event.content && !event.content.includes('Starting') && !event.content.includes('Processing')) {
          addMessage({ type: 'system', content: event.content });
        }
        break;

      case 'message':
        // General chat message response
        if (event.content) {
          addMessage({ type: 'system', content: event.content });
        }
        break;

      case 'resume':
        // Silently handle resume
        break;

      case 'interrupt':
        console.log('INTERRUPT RECEIVED:', event);
        
        // Handle interrupt - pause and wait for user input
        setIsLoading(false);
        const interruptInfo: InterruptData = {
          type: event.interrupt_type as 'question' | 'destination_selection',
          question: event.question || '',
          field: event.field,
          options: event.options,
          missing_info: event.missing_info,
          budget_allocation: event.budget_allocation,
        };
        
        setInterruptData(interruptInfo);
        
        addMessage({
          type: 'interrupt',
          content: event.question || 'Please provide more information',
          data: {
            type: event.interrupt_type,
            options: event.options,
            field: event.field,
            budget_allocation: event.budget_allocation,
          },
        });
        break;

      case 'step':
        setCurrentStep((prev) => prev + 1);
        addMessage({
          type: 'step',
          step: event.step,
          content: event.content || 'Processing...',
          data: event.data,
        });
        
        // Track selected season
        if (event.data?.season) {
          setSelectedSeason(event.data.season);
        }
        break;

      case 'research':
        setCurrentStep((prev) => prev + 1);
        addMessage({
          type: 'research',
          step: event.step,
          content: event.content || 'Researching destinations...',
          data: event.data,
        });
        break;

      case 'analysis':
        setCurrentStep((prev) => prev + 1);
        addMessage({
          type: 'analysis',
          step: event.step,
          content: event.content || 'Analyzing options...',
          data: event.data,
        });
        break;

      case 'season':
        setCurrentStep((prev) => prev + 1);
        addMessage({
          type: 'season',
          step: event.step,
          content: event.content || 'Season recommendations...',
          data: event.data,
        });
        break;

      case 'planning':
        setCurrentStep((prev) => prev + 1);
        addMessage({
          type: 'planning',
          step: event.step,
          content: event.content || 'Planning itinerary...',
          data: event.data,
        });
        break;

      case 'result':
        setCurrentStep(8);
        addMessage({
          type: 'result',
          step: event.step,
          content: event.content || 'Complete!',
          data: event,
        });
        break;

      case 'error':
        addMessage({ type: 'error', content: event.content || 'An error occurred.' });
        setIsLoading(false);
        break;
    }
  };

  const renderSeasonIcon = (season: string, className: string = 'w-4 h-4') => {
    const Icon = SEASON_ICONS[season as keyof typeof SEASON_ICONS];
    if (!Icon) return null;
    return <Icon className={`${className} ${SEASON_COLORS[season as keyof typeof SEASON_COLORS]}`} />;
  };

  return (
    <div className={`min-h-screen bg-gradient-to-br ${selectedSeason ? SEASON_GRADIENTS[selectedSeason as keyof typeof SEASON_GRADIENTS] : 'from-blue-50 via-indigo-50 to-purple-50'} dark:from-gray-900 dark:to-gray-800 transition-all duration-1000`}>
      <div className="max-w-5xl mx-auto p-4 h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white/90 backdrop-blur dark:bg-gray-800/90 rounded-t-2xl shadow-xl p-6 mb-4 border-b-4 border-indigo-500">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-100 rounded-xl">
                <Plane className="w-8 h-8 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-800 dark:text-white flex items-center gap-2">
                  WakeWander: AI Travel Planner
                  <Sparkles className="w-5 h-5 text-yellow-500" />
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Intelligent Season-Aware Planning • Powered by LangGraph
                </p>
              </div>
            </div>
            
            {selectedSeason && (
              <div className="flex items-center gap-2 bg-gradient-to-r from-white to-gray-50 px-4 py-2 rounded-full border-2 border-gray-200">
                {renderSeasonIcon(selectedSeason, 'w-6 h-6')}
                <span className="font-semibold text-gray-700 capitalize">{selectedSeason}</span>
              </div>
            )}
          </div>
          
          {isLoading && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                  <span className="font-medium">Creating your perfect trip...</span>
                </div>
                <span className="text-xs text-gray-500">Step {currentStep}/8</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2.5 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${(currentStep / 8) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 bg-white/90 backdrop-blur dark:bg-gray-800/90 shadow-xl overflow-y-auto p-6 mb-4 rounded-lg">
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id}>
                {/* User Message */}
                {message.type === 'user' && (
                  <div className="flex justify-end">
                    <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-2xl px-5 py-3 max-w-2xl shadow-lg">
                      <p className="text-sm font-medium">{message.content}</p>
                    </div>
                  </div>
                )}

                {/* System Message */}
                {message.type === 'system' && (
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:bg-blue-900/20 rounded-2xl p-5 border-l-4 border-blue-500 shadow-sm">
                    <p className="text-gray-800 dark:text-gray-200 whitespace-pre-line leading-relaxed">
                      {message.content}
                    </p>
                  </div>
                )}

                {/* Interrupt - Question or Destination Selection */}
                {message.type === 'interrupt' && (
                  <div className="bg-gradient-to-r from-yellow-50 to-amber-50 dark:bg-yellow-900/20 rounded-2xl p-5 border-2 border-yellow-400 shadow-lg">
                    <div className="flex items-start gap-3 mb-4">
                      <div className="p-2 bg-yellow-200 rounded-lg">
                        <AlertCircle className="w-5 h-5 text-yellow-700" />
                      </div>
                      <div className="flex-1">
                        <div className="font-bold text-yellow-900 mb-1 text-lg">
                          {message.data?.type === 'destination_selection' ? '🌍 Choose Your Dream Destination' : '📝 Quick Question'}
                        </div>
                        <p className="text-gray-800 font-medium">{message.content}</p>
                      </div>
                    </div>

                    {/* Destination Selection */}
                    {message.data?.type === 'destination_selection' && message.data?.options && (
                      <div className="space-y-3">
                        {message.data.budget_allocation && (
                          <div className="bg-white/80 backdrop-blur p-4 rounded-xl mb-4 border border-gray-200">
                            <div className="flex items-center gap-2 mb-3">
                              <DollarSign className="w-5 h-5 text-green-600" />
                              <div className="text-sm font-bold text-gray-800">Your Budget Breakdown</div>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                              <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-3 rounded-lg">
                                <div className="text-xs text-gray-600 mb-1">Daily Budget</div>
                                <div className="text-lg font-bold text-green-700">
                                  ${message.data.budget_allocation.daily_budget?.toFixed(2)}
                                </div>
                              </div>
                              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 p-3 rounded-lg">
                                <div className="text-xs text-gray-600 mb-1">Accommodation</div>
                                <div className="text-lg font-bold text-blue-700">
                                  ${message.data.budget_allocation.accommodation_budget?.toFixed(2)}
                                </div>
                              </div>
                              <div className="bg-gradient-to-br from-orange-50 to-yellow-50 p-3 rounded-lg">
                                <div className="text-xs text-gray-600 mb-1">Food</div>
                                <div className="text-lg font-bold text-orange-700">
                                  ${message.data.budget_allocation.food_budget?.toFixed(2)}
                                </div>
                              </div>
                              <div className="bg-gradient-to-br from-purple-50 to-pink-50 p-3 rounded-lg">
                                <div className="text-xs text-gray-600 mb-1">Activities</div>
                                <div className="text-lg font-bold text-purple-700">
                                  ${message.data.budget_allocation.activities_budget?.toFixed(2)}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {message.data.options.map((option: any, index: number) => (
                          <button
                            key={index}
                            onClick={() => handleInterruptResponse(index)}
                            disabled={interruptData === null}
                            className="w-full bg-white hover:bg-gradient-to-r hover:from-indigo-50 hover:to-purple-50 border-2 border-gray-200 hover:border-indigo-400 hover:shadow-xl rounded-xl p-5 text-left transition-all transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed group"
                          >
                            <div className="flex justify-between items-start gap-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <MapPin className="w-5 h-5 text-indigo-600 group-hover:text-indigo-700" />
                                  <div className="font-bold text-lg text-gray-900 group-hover:text-indigo-700">
                                    {option.name}
                                  </div>
                                </div>
                                
                                <p className="text-sm text-gray-700 mb-3 leading-relaxed">
                                  {option.description}
                                </p>

                                {option.highlights && option.highlights.length > 0 && (
                                  <div className="flex flex-wrap gap-2 mb-3">
                                    {option.highlights.map((highlight: string, idx: number) => (
                                      <span key={idx} className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full">
                                        ✨ {highlight}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                
                                <div className="flex items-center gap-4 flex-wrap">
                                  {option.best_season && (
                                    <div className="flex items-center gap-1.5 bg-gray-100 px-3 py-1.5 rounded-lg">
                                      {renderSeasonIcon(option.best_season)}
                                      <span className="text-xs font-medium capitalize">
                                        Best: {option.best_season}
                                      </span>
                                    </div>
                                  )}
                                  {option.season_notes && (
                                    <div className="text-xs text-blue-700 font-medium bg-blue-50 px-3 py-1.5 rounded-lg">
                                      💡 {option.season_notes}
                                    </div>
                                  )}
                                </div>
                              </div>
                              
                              <div className="text-right flex-shrink-0">
                                <div className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white px-4 py-3 rounded-xl shadow-lg">
                                  <div className="text-2xl font-bold">
                                    ${option.avg_daily_cost}
                                  </div>
                                  <div className="text-xs opacity-90">per day</div>
                                </div>
                              </div>
                            </div>
                            
                            <div className="mt-3 flex items-center gap-2 text-indigo-600 font-medium text-sm opacity-0 group-hover:opacity-100 transition-opacity">
                              <span>Select this destination</span>
                              <ArrowRight className="w-4 h-4" />
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Question Input */}
                    {message.data?.type === 'question' && interruptData && (
                      <div className="mt-4 space-y-3">
                        {message.data.field === 'season' ? (
                          <div className="grid grid-cols-2 gap-3">
                            {['spring', 'summer', 'fall', 'winter'].map((season) => (
                              <button
                                key={season}
                                onClick={() => handleInterruptResponse(season)}
                                className={`flex items-center justify-center gap-3 p-4 bg-white hover:bg-gradient-to-r ${
                                  season === 'spring' ? 'hover:from-pink-50 hover:to-rose-50' :
                                  season === 'summer' ? 'hover:from-yellow-50 hover:to-orange-50' :
                                  season === 'fall' ? 'hover:from-orange-50 hover:to-amber-50' :
                                  'hover:from-blue-50 hover:to-cyan-50'
                                } border-2 border-gray-300 hover:border-indigo-400 rounded-xl hover:shadow-lg transition-all transform hover:scale-105`}
                              >
                                {renderSeasonIcon(season, 'w-6 h-6')}
                                <span className="font-semibold capitalize text-gray-800">{season}</span>
                              </button>
                            ))}
                          </div>
                        ) : (
                          <form
                            onSubmit={(e) => {
                              e.preventDefault();
                              if (userResponse.trim()) {
                                handleInterruptResponse(userResponse);
                              }
                            }}
                            className="flex gap-3"
                          >
                            <div className="flex-1 relative">
                              <input
                                type={message.data.field === 'duration_days' || message.data.field === 'budget' || message.data.field === 'num_people' ? 'number' : 'text'}
                                value={userResponse}
                                onChange={(e) => setUserResponse(e.target.value)}
                                placeholder={
                                  message.data.field === 'duration_days' ? 'e.g., 5' :
                                  message.data.field === 'budget' ? 'e.g., 2000' :
                                  message.data.field === 'num_people' ? 'e.g., 2' :
                                  message.data.field === 'destination' ? 'e.g., Paris, France' :
                                  'Your answer...'
                                }
                                className="w-full px-5 py-3 border-2 border-gray-300 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 text-lg"
                                autoFocus
                              />
                              {message.data.field === 'duration_days' && (
                                <Calendar className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                              )}
                              {message.data.field === 'budget' && (
                                <DollarSign className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                              )}
                              {message.data.field === 'num_people' && (
                                <Users className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                              )}
                            </div>
                            <button
                              type="submit"
                              disabled={!userResponse.trim()}
                              className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
                            >
                              Submit
                            </button>
                          </form>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Step Complete */}
                {message.type === 'step' && (
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:bg-green-900/20 rounded-2xl p-4 border-l-4 border-green-500 shadow-sm">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="font-semibold text-green-800 mb-1">{message.step}</div>
                        <div className="text-gray-700">{message.content}</div>
                        
                        {message.data?.season && (
                          <div className="mt-2 inline-flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-green-200">
                            {renderSeasonIcon(message.data.season)}
                            <span className="text-sm font-medium capitalize">
                              {message.data.season} Season
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Research Results */}
                {message.type === 'research' && (
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:bg-purple-900/20 rounded-2xl p-5 border-l-4 border-purple-500 shadow-sm">
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-5 h-5 text-purple-600 mt-0.5" />
                      <div className="flex-1">
                        <div className="font-bold text-purple-800 mb-2">{message.step}</div>
                        <div className="text-gray-700 mb-3">{message.content}</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Season Recommendations */}
{/* Season Recommendations */}
                {message.type === 'season' && (
                  <div className={`bg-gradient-to-r ${selectedSeason ? SEASON_GRADIENTS[selectedSeason as keyof typeof SEASON_GRADIENTS] : 'from-yellow-50 to-orange-50'} dark:from-yellow-900/20 dark:to-orange-900/20 rounded-2xl p-5 border-2 border-yellow-300 shadow-lg`}>
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-white rounded-lg shadow-sm">
                        {selectedSeason && renderSeasonIcon(selectedSeason, 'w-6 h-6')}
                      </div>
                      <div className="flex-1">
                        <div className="font-bold text-yellow-900 mb-2 text-lg">{message.step}</div>
                        <p className="text-gray-800 leading-relaxed">{message.content}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Day Planning */}
                {message.type === 'planning' && (
                  <div className="bg-gradient-to-r from-orange-50 to-amber-50 dark:bg-orange-900/20 rounded-2xl p-4 border-l-4 border-orange-500 shadow-sm">
                    <div className="font-semibold text-orange-800 mb-2">{message.step}</div>
                    <div className="text-gray-700 whitespace-pre-line">{message.content}</div>
                  </div>
                )}

                {/* Final Result */}
                {message.type === 'result' && message.data?.itinerary && (
                  <div className="bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 rounded-2xl p-6 border-2 border-green-400 shadow-xl">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl shadow-lg">
                        <CheckCircle2 className="w-8 h-8 text-white" />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-gray-900">
                          🎉 Your Perfect Trip is Ready!
                        </h3>
                        <p className="text-gray-600">Everything planned and ready to go</p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                      <div className="bg-white p-4 rounded-xl shadow-md border border-gray-200">
                        <MapPin className="w-6 h-6 text-indigo-600 mb-2" />
                        <div className="text-xs text-gray-600 mb-1">Destination</div>
                        <div className="font-bold text-lg text-gray-900">{message.data.itinerary.destination}</div>
                      </div>
                      <div className="bg-white p-4 rounded-xl shadow-md border border-gray-200">
                        <Calendar className="w-6 h-6 text-purple-600 mb-2" />
                        <div className="text-xs text-gray-600 mb-1">Duration</div>
                        <div className="font-bold text-lg text-gray-900">{message.data.itinerary.duration_days} days</div>
                      </div>
                      <div className="bg-white p-4 rounded-xl shadow-md border border-gray-200">
                        <DollarSign className="w-6 h-6 text-green-600 mb-2" />
                        <div className="text-xs text-gray-600 mb-1">Total Budget</div>
                        <div className="font-bold text-lg text-gray-900">${message.data.itinerary.total_budget}</div>
                      </div>
                    </div>

                    {message.data.itinerary.season && (
                      <div className={`bg-white p-4 rounded-xl mb-4 border-2 ${
                        message.data.itinerary.season === 'spring' ? 'border-pink-300' :
                        message.data.itinerary.season === 'summer' ? 'border-yellow-300' :
                        message.data.itinerary.season === 'fall' ? 'border-orange-300' :
                        'border-blue-300'
                      }`}>
                        <div className="flex items-center gap-3 mb-3">
                          {renderSeasonIcon(message.data.itinerary.season, 'w-6 h-6')}
                          <span className="font-bold text-lg capitalize text-gray-900">
                            {message.data.itinerary.season} Season Trip
                          </span>
                        </div>
                        {message.data.itinerary.season_recommendations && (
                          <p className="text-sm text-gray-700 leading-relaxed pl-9">
                            {message.data.itinerary.season_recommendations}
                          </p>
                        )}
                      </div>
                    )}

                    {message.data.itinerary.num_people && message.data.itinerary.num_people > 1 && (
                      <div className="bg-blue-50 p-3 rounded-lg mb-4 flex items-center gap-2">
                        <Users className="w-5 h-5 text-blue-600" />
                        <span className="text-sm font-medium text-gray-700">
                          Planning for {message.data.itinerary.num_people} travelers
                        </span>
                      </div>
                    )}

                    <div className="bg-white p-5 rounded-xl shadow-md border border-gray-200">
                      <h4 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Calendar className="w-5 h-5 text-indigo-600" />
                        Daily Itinerary
                      </h4>
                      <div className="space-y-3">
                        {message.data.itinerary.daily_itinerary?.map((day: any, idx: number) => (
                          <div 
                            key={day.day} 
                            className="pb-3 border-b last:border-b-0 border-gray-200 hover:bg-gray-50 p-3 rounded-lg transition-colors"
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex items-center gap-2">
                                <div className="w-8 h-8 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-bold text-sm">
                                  {day.day}
                                </div>
                                <div>
                                  <div className="font-semibold text-gray-900">
                                    {day.title || `Day ${day.day}`}
                                  </div>
                                  {day.weather && (
                                    <div className="text-xs text-gray-600 flex items-center gap-1">
                                      {day.weather.includes('☀') || day.weather.toLowerCase().includes('sun') ? '☀️' :
                                       day.weather.includes('🌧') || day.weather.toLowerCase().includes('rain') ? '🌧️' :
                                       day.weather.includes('☁') || day.weather.toLowerCase().includes('cloud') ? '☁️' : '🌤️'}
                                      {day.weather}
                                    </div>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold text-green-700">
                                  ${day.daily_total?.toFixed(2) || '0.00'}
                                </div>
                                <div className="text-xs text-gray-500">total</div>
                              </div>
                            </div>
                            
                            {day.season_notes && (
                              <div className="bg-blue-50 border-l-4 border-blue-400 p-2 rounded text-xs text-blue-800 mt-2">
                                💡 <span className="font-medium">{day.season_notes}</span>
                              </div>
                            )}
                            
                            {day.activities && day.activities.length > 0 && (
                              <div className="mt-2 text-xs text-gray-600">
                                {day.activities.length} {day.activities.length === 1 ? 'activity' : 'activities'} planned
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                      
                      <div className="mt-4 pt-4 border-t-2 border-gray-300">
                        <div className="flex justify-between items-center">
                          <div className="text-sm text-gray-600">
                            Total Cost Estimate
                          </div>
                          <div className="text-2xl font-bold text-gray-900">
                            ${message.data.itinerary.actual_cost?.toFixed(2) || '0.00'}
                          </div>
                        </div>
                        {message.data.itinerary.budget_remaining !== undefined && (
                          <div className={`mt-2 text-sm ${message.data.itinerary.budget_remaining >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                            {message.data.itinerary.budget_remaining >= 0 ? '✓' : '⚠'} Budget remaining: 
                            <span className="font-semibold ml-1">
                              ${Math.abs(message.data.itinerary.budget_remaining).toFixed(2)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {message.data.itinerary_id && (
                      <div className="mt-4 p-3 bg-gray-100 rounded-lg text-xs text-gray-600">
                        <span className="font-medium">Itinerary ID:</span> {message.data.itinerary_id}
                      </div>
                    )}
                  </div>
                )}

                {/* Error */}
                {message.type === 'error' && (
                  <div className="bg-red-50 rounded-2xl p-4 border-l-4 border-red-500 shadow-sm">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                      <div className="text-red-800">{message.content}</div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <div className="bg-white/90 backdrop-blur dark:bg-gray-800/90 rounded-b-2xl shadow-xl p-5 border-t-4 border-indigo-500">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="e.g., 'Paris for 5 days in spring with $2000 budget for 2 people'"
                  disabled={isLoading || interruptData !== null}
                  className="w-full px-5 py-4 pr-12 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 dark:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed text-base transition-all"
                />
                <Plane className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              </div>
              <button
                type="submit"
                disabled={isLoading || !input.trim() || interruptData !== null}
                className="px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 font-semibold shadow-lg hover:shadow-xl flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="hidden sm:inline">Planning...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    <span className="hidden sm:inline">Plan Trip</span>
                  </>
                )}
              </button>
            </div>
            
            <div className="flex items-center justify-between text-xs">
              <p className="text-gray-600">
                {interruptData 
                  ? '👆 Please respond to the question above to continue'
                  : 'Include season for personalized recommendations'
                }
              </p>
              <div className="flex items-center gap-2">
                {Object.entries(SEASON_ICONS).map(([season, Icon]) => (
                  <Icon 
                    key={season} 
                    className={`w-4 h-4 ${SEASON_COLORS[season as keyof typeof SEASON_COLORS]} opacity-60`}
                  />
                ))}
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}