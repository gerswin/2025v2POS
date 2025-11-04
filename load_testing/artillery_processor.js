/**
 * Artillery.js processor for Venezuelan POS System load testing
 */

const { v4: uuidv4 } = require('uuid');

module.exports = {
  // Generate random UUIDs for testing
  generateUUID: function(context, events, done) {
    context.vars.random_uuid = uuidv4();
    return done();
  },

  // Generate random customer data
  generateCustomerData: function(context, events, done) {
    const names = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Carmen', 'José', 'Isabel'];
    const surnames = ['García', 'Rodríguez', 'López', 'Martínez', 'González', 'Pérez', 'Sánchez', 'Ramírez'];
    
    context.vars.customer_name = names[Math.floor(Math.random() * names.length)];
    context.vars.customer_surname = surnames[Math.floor(Math.random() * surnames.length)];
    context.vars.customer_phone = `+58414${Math.floor(Math.random() * 9000000) + 1000000}`;
    context.vars.customer_email = `${context.vars.customer_name.toLowerCase()}${Math.floor(Math.random() * 1000)}@example.com`;
    context.vars.customer_cedula = `V-${Math.floor(Math.random() * 90000000) + 10000000}`;
    
    return done();
  },

  // Generate random event data
  generateEventData: function(context, events, done) {
    const eventTypes = ['concert', 'theater', 'sports', 'conference'];
    const venues = ['Teatro Nacional', 'Estadio Olímpico', 'Centro de Convenciones', 'Auditorio Principal'];
    
    context.vars.event_type = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    context.vars.venue_name = venues[Math.floor(Math.random() * venues.length)];
    context.vars.event_name = `Test Event ${Math.floor(Math.random() * 1000)}`;
    
    return done();
  },

  // Log performance metrics
  logMetrics: function(context, events, done) {
    events.on('response', function(data) {
      const responseTime = data.latency;
      const statusCode = data.statusCode;
      
      // Log slow responses
      if (responseTime > 1000) {
        console.log(`SLOW RESPONSE: ${data.url} - ${responseTime}ms - ${statusCode}`);
      }
      
      // Log errors
      if (statusCode >= 400) {
        console.log(`ERROR RESPONSE: ${data.url} - ${statusCode} - ${responseTime}ms`);
      }
    });
    
    return done();
  },

  // Custom authentication helper
  authenticate: function(context, events, done) {
    // This would be called before scenarios that need authentication
    // The actual authentication is handled in the scenario flows
    return done();
  }
};