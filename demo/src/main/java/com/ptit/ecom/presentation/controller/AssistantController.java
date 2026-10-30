package com.ptit.ecom.presentation.controller;

import com.ptit.ecom.application.service.AssistantReply;
import com.ptit.ecom.application.service.AssistantService;

/**
 * Controller of the AI shopping assistant (UC10).
 * The question may be typed or spoken (transcribed by Whisper first).
 */
public class AssistantController {
    private AssistantService assistantService;

    public AssistantController(AssistantService assistantService) {
        this.assistantService = assistantService;
    }

    public AssistantReply ask(String customerId, String message) {
        return assistantService.ask(customerId, message);
    }
}
