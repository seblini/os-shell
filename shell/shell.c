#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_LINE 1<<10

typedef enum {
	EXIT,
	PIPE,
	REDIRECT_IN,
	REDIRECT_OUT,
	BACKGROUND,
	DEFAULT,
	END
} TokenType;

typedef struct {
	TokenType type;
	char *value;
} Token;

void assign_token_type(Token *token) {
	if (token->value == NULL) {
		token->type = END;
	} else if (strcmp(token->value, "exit") == 0) {
		token->type = EXIT;
	} else if (strcmp(token->value, "|") == 0) {
		token->type = PIPE;
	} else if (strcmp(token->value, "<") == 0) {
		token->type = REDIRECT_IN;
	} else if (strcmp(token->value, ">") == 0) {
		token->type = REDIRECT_OUT;
	} else if (strcmp(token->value, "&") == 0) {
		token->type = BACKGROUND;
	} else {
		token->type = DEFAULT;
	}
}

Token *parse_tokens(char *line, int n) {
	/*
	* Parses tokens from a line of input
	*
	* Parameters:
	*   line - the line of input
	*   n    - the length of the line
	*
	* Returns:
	*   An array of tokens terminated by a token with type END.
	*	Caller is responsible for freeing the array,
	*/

	Token *tokens;
	int i;
	int argCount = 0;

	// count args
	for (i = 1; i < n; i++) {
		if (line[i] == '\0') {
			break;
		}

		// counts groups of consecutive delimiter character: space, tab, newline
		switch (line[i]) {
			case ' ': case '\t': case '\n':
				switch (line[i-1]) {
					case ' ': case '\t': case '\n':
						break;
					default:
						argCount++;
				}
				break;
		}
	}

	tokens = malloc(sizeof(Token) * (argCount + 1));

	// populate args
	i = 0;
	tokens[i].value = strtok(line, " \t\n");
	assign_token_type(&tokens[i]);
	while (tokens[i++].value != NULL) {
		tokens[i].value = strtok(NULL, " \t\n");
		assign_token_type(&tokens[i]);
	}

	return tokens;
}

int main(int argc, char *argv[]) {
	char line[MAX_LINE];
	Token *tokens;
	int i;

	int rc;

	fgets(line, MAX_LINE, stdin);
	tokens = parse_tokens(line, strlen(line));

	switch (tokens[0].type) {
		case EXIT:
			exit(0);
			break;
		case PIPE: case REDIRECT_IN: case REDIRECT_OUT: case BACKGROUND: case END:
			fprintf(stderr, "Invalid command: %s\n", tokens[0].value);
			exit(1);
			break;
		default:
			break;
	}

	i = 0;
	while (tokens[i].type != END) {
		fprintf(stdout, "%s ", tokens[i].value);
		i++;
	}

	free(tokens);

    return 0;
}
